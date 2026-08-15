#!/usr/bin/env python3
"""Seed KYROX Core identity data for Fair CRM development.

Platform-level unrestricted access is represented only by
``identity_users.is_super_admin`` and is never represented by a role
assignment. The protected ``organization_admin`` role is kept available for
non-Super-Admin organization members.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from psycopg2 import sql

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
STATE_FILE = SCRIPTS_DIR / ".dev_state.json"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from fair_crm_role_matrix import (  # noqa: E402
    ALL_FAIR_CRM_PERMISSIONS,
    DEV_ROLE_USERS,
    ROLE_MATRIX_VERSION,
    permissions_for_role,
    role_slugs,
)

DEV_ORG_ID = os.environ.get(
    "FAIR_CRM_DEV_ORGANIZATION_ID", "00000000-0000-4000-8000-000000000010"
)
DEV_ORG_NAME = os.environ.get("FAIR_CRM_DEV_ORGANIZATION_NAME", "Fair CRM Dev Org")
DEV_ORG_SLUG = os.environ.get("FAIR_CRM_DEV_ORGANIZATION_SLUG", "fair-crm-dev")
CORE_DB_URL = os.environ.get(
    "KYROX_CORE_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/kyrox_core",
)
MIN_CORE_MIGRATION_REVISION = "20260815_0050"
DEV_SEED_ENV_FILE_HINT = "/etc/fair-crm/dev-seed.env"


class SeedError(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _connect(db_url: str):
    return psycopg2.connect(db_url)


def password_fingerprint(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()[:12]


def require_dev_password() -> str:
    raw = os.environ.get("DEV_USER_PASSWORD", "")
    password = raw.strip()
    if not password:
        raise SeedError(
            "DEV_USER_PASSWORD is required and must not be empty.\n"
            "Local: export DEV_USER_PASSWORD before running this script.\n"
            f"Server: create {DEV_SEED_ENV_FILE_HINT} with DEV_USER_PASSWORD=<value>."
        )
    return password


def password_hash_matches(stored_hash: str, password: str) -> bool:
    try:
        return bool(PasswordHasher().verify(stored_hash, password))
    except (VerifyMismatchError, ValueError, TypeError):
        return False


def ensure_database_exists(admin_url: str, db_name: str) -> None:
    conn = _connect(admin_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cur.fetchone() is None:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
                print(f"Created database {db_name}")
    finally:
        conn.close()


def assert_core_migration_ready(cur) -> str:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'alembic_version'
        )
        """
    )
    if not cur.fetchone()[0]:
        raise SeedError("Core database has no alembic_version table; run Core migrations first.")

    cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
    row = cur.fetchone()
    if row is None:
        raise SeedError("Core alembic_version is empty; run Core migrations first.")

    current = str(row[0])
    if current < MIN_CORE_MIGRATION_REVISION:
        raise SeedError(
            f"Core migration {current} is below required {MIN_CORE_MIGRATION_REVISION}."
        )
    print(f"Core migration OK: {current}")
    return current


def load_required_roles(cur) -> dict[str, str]:
    """Load Core-owned roles without creating or modifying governance data."""
    role_ids: dict[str, str] = {}
    for slug in role_slugs():
        cur.execute(
            """
            SELECT id, role_kind, is_assignable, is_protected,
                   auto_include_new_permissions
            FROM identity_roles
            WHERE scope = 'organization' AND slug = %s
              AND organization_id IS NULL AND deleted_at IS NULL
            LIMIT 1
            """,
            (slug,),
        )
        row = cur.fetchone()
        if row is None:
            raise SeedError(
                f"Required Core role is missing: {slug}. Run Core migrations first."
            )
        if slug == "organization_admin" and tuple(row[1:]) != (
            "protected_global",
            True,
            True,
            True,
        ):
            raise SeedError(
                "Core OrganizationAdmin governance flags are invalid; "
                "run the current Core migrations instead of repairing them in Fair CRM seed."
            )
        role_ids[slug] = str(row[0])
    return role_ids


def ensure_dev_organization(cur) -> str:
    cur.execute(
        "SELECT id FROM identity_organizations WHERE id = %s AND deleted_at IS NULL LIMIT 1",
        (DEV_ORG_ID,),
    )
    row = cur.fetchone()
    if row:
        return str(row[0])

    cur.execute(
        "SELECT id FROM identity_organizations WHERE slug = %s AND deleted_at IS NULL LIMIT 1",
        (DEV_ORG_SLUG,),
    )
    slug_row = cur.fetchone()
    if slug_row and str(slug_row[0]) != DEV_ORG_ID:
        raise SeedError(f"Organization slug '{DEV_ORG_SLUG}' is already in use.")

    now = _now()
    cur.execute(
        """
        INSERT INTO identity_organizations (
            id, name, slug, status, created_at, updated_at, deleted_at
        ) VALUES (%s, %s, %s, 'active', %s, %s, NULL)
        """,
        (DEV_ORG_ID, DEV_ORG_NAME, DEV_ORG_SLUG, now, now),
    )
    print(f"Created dev organization: {DEV_ORG_NAME}")
    return DEV_ORG_ID


def sync_dev_user_password(cur, *, user_id: str, email: str, password: str) -> None:
    ph = PasswordHasher()
    cur.execute("SELECT password_hash FROM identity_users WHERE id = %s LIMIT 1", (user_id,))
    row = cur.fetchone()
    if row is None:
        raise SeedError(f"Cannot sync password; user missing: {email}")

    stored_hash = str(row[0] or "")
    if stored_hash and password_hash_matches(stored_hash, password) and not ph.check_needs_rehash(stored_hash):
        return

    cur.execute(
        """
        UPDATE identity_users
        SET password_hash = %s, status = 'active', updated_at = %s, deleted_at = NULL
        WHERE id = %s
        """,
        (ph.hash(password), _now(), user_id),
    )


def ensure_dev_user(cur, *, user_id: str, email: str, password: str) -> str:
    """Create bootstrap user once; never overwrite is_super_admin on existing rows."""
    cur.execute("SELECT id, email FROM identity_users WHERE id = %s LIMIT 1", (user_id,))
    row = cur.fetchone()
    if row:
        if str(row[1]) != email:
            cur.execute(
                "UPDATE identity_users SET email = %s, updated_at = %s WHERE id = %s",
                (email, _now(), user_id),
            )
        sync_dev_user_password(cur, user_id=user_id, email=email, password=password)
        return user_id

    cur.execute("SELECT id FROM identity_users WHERE email = %s LIMIT 1", (email,))
    by_email = cur.fetchone()
    if by_email:
        existing_id = str(by_email[0])
        sync_dev_user_password(cur, user_id=existing_id, email=email, password=password)
        return existing_id

    now = _now()
    cur.execute(
        """
        INSERT INTO identity_users (
            id, email, password_hash, status, is_super_admin,
            created_at, updated_at, deleted_at
        ) VALUES (%s, %s, %s, 'active', TRUE, %s, %s, NULL)
        """,
        (user_id, email, PasswordHasher().hash(password), now, now),
    )
    print(f"Created bootstrap Super Admin: {email}")
    return user_id


def ensure_membership(cur, user_id: str, organization_id: str) -> None:
    cur.execute(
        """
        SELECT id, status FROM identity_memberships
        WHERE user_id = %s AND organization_id = %s AND deleted_at IS NULL
        LIMIT 1
        """,
        (user_id, organization_id),
    )
    row = cur.fetchone()
    if row:
        if row[1] != "active":
            cur.execute(
                "UPDATE identity_memberships SET status = 'active', updated_at = %s WHERE id = %s",
                (_now(), str(row[0])),
            )
        return

    now = _now()
    cur.execute(
        """
        INSERT INTO identity_memberships (
            id, user_id, organization_id, status,
            invited_at, joined_at, created_at, updated_at, deleted_at
        ) VALUES (%s, %s, %s, 'active', NULL, %s, %s, %s, NULL)
        """,
        (str(uuid.uuid4()), user_id, organization_id, now, now, now),
    )


def ensure_user_role_assignment(
    cur, *, user_id: str, organization_id: str, role_id: str
) -> None:
    cur.execute(
        """
        SELECT id FROM identity_user_roles
        WHERE user_id = %s AND organization_id = %s
          AND role_id = %s
          AND status = 'active' AND revoked_at IS NULL
        LIMIT 1
        """,
        (user_id, organization_id, role_id),
    )
    if cur.fetchone():
        return

    now = _now()
    cur.execute(
        """
        INSERT INTO identity_user_roles (
            id, user_id, organization_id, role_id,
            status, assigned_at, revoked_at, assigned_by, created_at
        ) VALUES (%s, %s, %s, %s, 'active', %s, NULL, %s, %s)
        """,
        (
            str(uuid.uuid4()),
            user_id,
            organization_id,
            role_id,
            now,
            user_id,
            now,
        ),
    )


def user_is_super_admin(cur, user_id: str) -> bool:
    cur.execute(
        "SELECT is_super_admin FROM identity_users WHERE id = %s LIMIT 1",
        (user_id,),
    )
    row = cur.fetchone()
    return bool(row and row[0])


def remove_super_admin_role_assignments(cur, user_id: str) -> None:
    cur.execute("DELETE FROM identity_user_roles WHERE user_id = %s", (user_id,))
    if cur.rowcount:
        print(f"Removed {cur.rowcount} invalid Super Admin role assignment(s)")


def main() -> int:
    try:
        dev_password = require_dev_password()
    except SeedError as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1

    admin_url = os.environ.get(
        "POSTGRES_ADMIN_URL",
        "postgresql://postgres:postgres@localhost:5432/postgres",
    )
    ensure_database_exists(admin_url, "kyrox_core")

    conn = _connect(CORE_DB_URL)
    conn.autocommit = False
    role_users_state: dict[str, dict[str, str]] = {}
    org_id: str | None = None

    try:
        with conn.cursor() as cur:
            assert_core_migration_ready(cur)
            role_ids = load_required_roles(cur)

            org_id = ensure_dev_organization(cur)

            for role_slug, email, user_id in DEV_ROLE_USERS:
                resolved_user_id = ensure_dev_user(
                    cur, user_id=user_id, email=email, password=dev_password
                )
                is_super_admin = user_is_super_admin(cur, resolved_user_id)
                if is_super_admin:
                    remove_super_admin_role_assignments(cur, resolved_user_id)
                    assignment_source = "identity_users.is_super_admin"
                else:
                    ensure_membership(cur, resolved_user_id, org_id)
                    ensure_user_role_assignment(
                        cur,
                        user_id=resolved_user_id,
                        organization_id=org_id,
                        role_id=role_ids[role_slug],
                    )
                    assignment_source = "identity_user_roles.role_id"
                role_users_state[role_slug] = {
                    "email": email,
                    "user_id": resolved_user_id,
                    "role_id": role_ids[role_slug],
                    "assignment_source": assignment_source,
                    "permission_count": str(len(permissions_for_role(role_slug))),
                }

        conn.commit()
    except Exception as exc:
        conn.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()

    admin_state = role_users_state["organization_admin"]
    state = {
        "email": admin_state["email"],
        "password_source": "DEV_USER_PASSWORD",
        "password_length": len(dev_password),
        "password_fingerprint": password_fingerprint(dev_password),
        "user_id": admin_state["user_id"],
        "organization_id": org_id,
        "organization_admin_role_id": admin_state["role_id"],
        "is_super_admin_source": "identity_users.is_super_admin",
        "fair_crm_permission_count": len(ALL_FAIR_CRM_PERMISSIONS),
        "role_matrix_version": ROLE_MATRIX_VERSION,
        "roles": role_users_state,
    }
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"Wrote dev state to {STATE_FILE}")
    print(
        "Seed complete — platform Super Admin is DB-controlled and has no role assignment; "
        "OrganizationAdmin remains available to organization members."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

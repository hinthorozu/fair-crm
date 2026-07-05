#!/usr/bin/env python3
"""Seed KYROX Core identity data for local Fair CRM development.

Runs against the Core database only (fair-crm repo script; does not modify kyrox-core code).
Creates dev organization, role templates with FAIR CRM permission matrix, and dev users per role.

Requires Core Alembic revision >= 20260701_0026 (fair_crm product permission catalog).
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
from argon2 import PasswordHasher
from psycopg2 import sql

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
STATE_FILE = SCRIPTS_DIR / ".dev_state.json"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from fair_crm_role_matrix import (  # noqa: E402
    ALL_FAIR_CRM_PERMISSIONS,
    DEV_ROLE_USERS,
    ROLE_DEFINITIONS,
    ROLE_MATRIX_VERSION,
    all_permissions_referenced,
    permissions_for_role,
    role_slugs,
)

DEV_PASSWORD = os.environ.get("DEV_USER_PASSWORD", "DevPassword123!")
DEV_ORG_ID = os.environ.get("FAIR_CRM_DEV_ORGANIZATION_ID", "00000000-0000-4000-8000-000000000010")
DEV_ORG_NAME = os.environ.get("FAIR_CRM_DEV_ORGANIZATION_NAME", "Fair CRM Dev Org")
DEV_ORG_SLUG = os.environ.get("FAIR_CRM_DEV_ORGANIZATION_SLUG", "fair-crm-dev")

CORE_DB_URL = os.environ.get(
    "KYROX_CORE_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/kyrox_core",
)

MIN_CORE_MIGRATION_REVISION = "20260701_0026"


class SeedError(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _connect(db_url: str):
    return psycopg2.connect(db_url)


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
        raise SeedError(
            "Core database has no alembic_version table. "
            "Run kyrox-core migrations first: cd kyrox-core && python -m alembic upgrade head"
        )

    cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
    row = cur.fetchone()
    if row is None:
        raise SeedError(
            "Core alembic_version is empty. "
            "Run kyrox-core migrations first: cd kyrox-core && python -m alembic upgrade head"
        )

    current = str(row[0])
    if current < MIN_CORE_MIGRATION_REVISION:
        raise SeedError(
            f"Core migration {current} is below required {MIN_CORE_MIGRATION_REVISION}. "
            "Run: cd kyrox-core && python -m alembic upgrade head"
        )
    print(f"Core migration OK: {current} (required >= {MIN_CORE_MIGRATION_REVISION})")
    return current


def load_permission_ids(cur, codes: frozenset[str]) -> dict[str, str]:
    cur.execute(
        "SELECT code, id FROM identity_permissions WHERE code = ANY(%s)",
        (sorted(codes),),
    )
    found = {str(code): str(perm_id) for code, perm_id in cur.fetchall()}
    missing = [code for code in sorted(codes) if code not in found]
    if missing:
        raise SeedError(
            "Missing permissions in Core catalog (run kyrox-core alembic upgrade head): "
            + ", ".join(missing)
        )
    return found


def ensure_role_templates(cur) -> dict[str, str]:
    role_ids: dict[str, str] = {}
    now = _now()
    for slug in role_slugs():
        definition = ROLE_DEFINITIONS[slug]
        name = str(definition["name"])
        cur.execute(
            """
            SELECT id FROM identity_roles
            WHERE scope = 'organization' AND slug = %s AND deleted_at IS NULL
            LIMIT 1
            """,
            (slug,),
        )
        row = cur.fetchone()
        if row:
            role_ids[slug] = str(row[0])
            continue
        role_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO identity_roles (
                id, name, slug, scope, is_system, created_at, updated_at, deleted_at
            ) VALUES (%s, %s, %s, 'organization', TRUE, %s, %s, NULL)
            """,
            (role_id, name, slug, now, now),
        )
        role_ids[slug] = role_id
        print(f"Created role template: {slug}")
    return role_ids


def grant_permissions_to_role(
    cur,
    role_id: str,
    permission_ids: dict[str, str],
    codes: frozenset[str],
    label: str,
) -> int:
    granted = 0
    for code in sorted(codes):
        cur.execute(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (role_id, permission_ids[code]),
        )
        if cur.rowcount:
            granted += 1
    print(f"Granted {label} ({granted} new, {len(codes)} total expected)")
    return granted


def count_role_permission_mappings(cur, role_id: str, codes: frozenset[str]) -> int:
    if not codes:
        return 0
    cur.execute(
        """
        SELECT COUNT(*)
        FROM identity_role_permissions rp
        JOIN identity_permissions p ON p.id = rp.permission_id
        WHERE rp.role_id = %s AND p.code = ANY(%s)
        """,
        (role_id, sorted(codes)),
    )
    return int(cur.fetchone()[0])


def ensure_dev_organization(cur) -> str:
    cur.execute(
        """
        SELECT id, slug FROM identity_organizations
        WHERE id = %s AND deleted_at IS NULL
        LIMIT 1
        """,
        (DEV_ORG_ID,),
    )
    row = cur.fetchone()
    if row:
        print(f"Dev organization already exists: {DEV_ORG_ID} (slug={row[1]})")
        return str(row[0])

    cur.execute(
        """
        SELECT id FROM identity_organizations
        WHERE slug = %s AND deleted_at IS NULL
        LIMIT 1
        """,
        (DEV_ORG_SLUG,),
    )
    slug_row = cur.fetchone()
    if slug_row and str(slug_row[0]) != DEV_ORG_ID:
        raise SeedError(
            f"Organization slug '{DEV_ORG_SLUG}' is already used by {slug_row[0]}. "
            "Set FAIR_CRM_DEV_ORGANIZATION_SLUG to a free slug or remove the conflicting org."
        )

    now = _now()
    cur.execute(
        """
        INSERT INTO identity_organizations (
            id, name, slug, status, created_at, updated_at, deleted_at
        ) VALUES (%s, %s, %s, 'active', %s, %s, NULL)
        """,
        (DEV_ORG_ID, DEV_ORG_NAME, DEV_ORG_SLUG, now, now),
    )
    print(f"Created dev organization: {DEV_ORG_NAME} ({DEV_ORG_ID}, slug={DEV_ORG_SLUG})")
    return DEV_ORG_ID


def ensure_dev_user(cur, *, user_id: str, email: str) -> str:
    cur.execute("SELECT id, email FROM identity_users WHERE id = %s LIMIT 1", (user_id,))
    row = cur.fetchone()
    if row:
        if str(row[1]) != email:
            cur.execute(
                "UPDATE identity_users SET email = %s, updated_at = %s WHERE id = %s",
                (email, _now(), user_id),
            )
            print(f"Updated dev user email for {user_id}: {row[1]} -> {email}")
        else:
            print(f"Dev user already exists: {email} ({user_id})")
        return user_id

    cur.execute("SELECT id FROM identity_users WHERE email = %s LIMIT 1", (email,))
    by_email = cur.fetchone()
    if by_email:
        existing_id = str(by_email[0])
        print(f"Dev user already exists by email ({email}): {existing_id}")
        return existing_id

    password_hash = PasswordHasher().hash(DEV_PASSWORD)
    now = _now()
    cur.execute(
        """
        INSERT INTO identity_users (
            id, email, password_hash, status, is_super_admin, created_at, updated_at, deleted_at
        ) VALUES (%s, %s, %s, 'active', FALSE, %s, %s, NULL)
        """,
        (user_id, email, password_hash, now, now),
    )
    print(f"Created dev user: {email} ({user_id})")
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
                """
                UPDATE identity_memberships
                SET status = 'active', updated_at = %s
                WHERE id = %s
                """,
                (_now(), str(row[0])),
            )
            print(f"Reactivated membership: {row[0]}")
        return

    now = _now()
    membership_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO identity_memberships (
            id, user_id, organization_id, status,
            invited_at, joined_at, created_at, updated_at, deleted_at
        ) VALUES (%s, %s, %s, 'active', NULL, %s, %s, %s, NULL)
        """,
        (membership_id, user_id, organization_id, now, now, now),
    )
    print(f"Created membership: {membership_id} user={user_id}")


def ensure_organization_role(cur, organization_id: str, role_template_id: str, *, slug: str) -> str:
    cur.execute(
        """
        SELECT id FROM identity_organization_roles
        WHERE organization_id = %s AND role_id = %s AND deleted_at IS NULL
        LIMIT 1
        """,
        (organization_id, role_template_id),
    )
    row = cur.fetchone()
    if row:
        return str(row[0])

    now = _now()
    org_role_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO identity_organization_roles (
            id, organization_id, role_id, status, is_default,
            created_at, updated_at, deleted_at
        ) VALUES (%s, %s, %s, 'active', FALSE, %s, %s, NULL)
        """,
        (org_role_id, organization_id, role_template_id, now, now),
    )
    print(f"Created organization role binding: {slug} -> {org_role_id}")
    return org_role_id


def ensure_user_role_assignment(
    cur,
    *,
    user_id: str,
    organization_id: str,
    organization_role_id: str,
    role_slug: str,
) -> None:
    cur.execute(
        """
        SELECT id FROM identity_user_roles
        WHERE user_id = %s
          AND organization_id = %s
          AND organization_role_id = %s
          AND status = 'active'
          AND revoked_at IS NULL
        LIMIT 1
        """,
        (user_id, organization_id, organization_role_id),
    )
    if cur.fetchone():
        return

    now = _now()
    user_role_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO identity_user_roles (
            id, user_id, organization_id, organization_role_id,
            status, assigned_at, revoked_at, assigned_by, created_at
        ) VALUES (%s, %s, %s, %s, 'active', %s, NULL, %s, %s)
        """,
        (user_role_id, user_id, organization_id, organization_role_id, now, user_id, now),
    )
    print(f"Assigned user {user_id} to role {role_slug}: {user_role_id}")


def main() -> int:
    admin_url = os.environ.get(
        "POSTGRES_ADMIN_URL",
        "postgresql://postgres:postgres@localhost:5432/postgres",
    )
    ensure_database_exists(admin_url, "kyrox_core")

    referenced_permissions = all_permissions_referenced()
    role_users_state: dict[str, dict[str, str]] = {}
    org_id: str | None = None
    role_template_ids: dict[str, str] = {}

    conn = _connect(CORE_DB_URL)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            assert_core_migration_ready(cur)
            permission_ids = load_permission_ids(cur, referenced_permissions)
            role_template_ids = ensure_role_templates(cur)

            for slug in role_slugs():
                codes = permissions_for_role(slug)
                if not codes:
                    continue
                grant_permissions_to_role(
                    cur,
                    role_template_ids[slug],
                    permission_ids,
                    codes,
                    f"{slug} role permissions",
                )
                mapped = count_role_permission_mappings(cur, role_template_ids[slug], codes)
                if mapped != len(codes):
                    raise SeedError(
                        f"Role {slug} has {mapped}/{len(codes)} permission mappings after seed."
                    )

            org_id = ensure_dev_organization(cur)
            org_role_ids: dict[str, str] = {}
            for slug, template_id in role_template_ids.items():
                if slug == "member" or not permissions_for_role(slug):
                    continue
                org_role_ids[slug] = ensure_organization_role(
                    cur, org_id, template_id, slug=slug
                )

            for role_slug, email, user_id in DEV_ROLE_USERS:
                resolved_user_id = ensure_dev_user(cur, user_id=user_id, email=email)
                ensure_membership(cur, resolved_user_id, org_id)
                org_role_id = org_role_ids[role_slug]
                ensure_user_role_assignment(
                    cur,
                    user_id=resolved_user_id,
                    organization_id=org_id,
                    organization_role_id=org_role_id,
                    role_slug=role_slug,
                )
                role_users_state[role_slug] = {
                    "email": email,
                    "user_id": resolved_user_id,
                    "role_template_id": role_template_ids[role_slug],
                    "organization_role_id": org_role_ids[role_slug],
                    "permission_count": str(len(permissions_for_role(role_slug))),
                }

            owner_codes = permissions_for_role("owner")
            owner_mapped = count_role_permission_mappings(
                cur, role_template_ids["owner"], owner_codes
            )
            if owner_mapped != len(owner_codes):
                raise SeedError(
                    f"Owner role has {owner_mapped}/{len(owner_codes)} permission mappings after seed."
                )

        conn.commit()
    except SeedError as exc:
        conn.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        conn.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()

    owner = role_users_state["owner"]
    state = {
        "email": owner["email"],
        "password": DEV_PASSWORD,
        "user_id": owner["user_id"],
        "organization_id": org_id,
        "owner_role_id": role_template_ids["owner"],
        "fair_crm_permission_count": len(ALL_FAIR_CRM_PERMISSIONS),
        "role_matrix_version": ROLE_MATRIX_VERSION,
        "roles": role_users_state,
    }
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"Wrote dev state to {STATE_FILE}")
    print(
        f"Seed complete — {len(DEV_ROLE_USERS)} dev users with role matrix "
        f"({len(role_slugs())} role templates, owner retains full fair_crm.* access)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Seed minimal KYROX Core identity data for local Fair CRM E2E validation.

Runs against the Core database only (fair-crm repo script; does not modify kyrox-core code).
Creates dev user, organization roles, and grants fair_crm.customers.* to the owner role.
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

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "scripts" / ".dev_state.json"

DEV_EMAIL = os.environ.get("DEV_USER_EMAIL", "dev@example.com")
DEV_PASSWORD = os.environ.get("DEV_USER_PASSWORD", "DevPassword123!")
CORE_DB_URL = os.environ.get(
    "KYROX_CORE_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/kyrox_core",
)

FAIR_CRM_PERMISSIONS = (
    "fair_crm.customers.create",
    "fair_crm.customers.read",
    "fair_crm.customers.update",
    "fair_crm.customers.archive",
)
AUDIT_READ_PERMISSION = "audit.logs.read"


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
                cur.execute(f'CREATE DATABASE "{db_name}"')
                print(f"Created database {db_name}")
    finally:
        conn.close()


def ensure_system_roles(cur) -> dict[str, str]:
    roles: dict[str, str] = {}
    now = _now()
    for slug, name in (("owner", "Owner"), ("member", "Member")):
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
            roles[slug] = str(row[0])
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
        roles[slug] = role_id
        print(f"Created system role: {slug}")
    return roles


def ensure_dev_user(cur) -> str:
    cur.execute("SELECT id FROM identity_users WHERE email = %s LIMIT 1", (DEV_EMAIL,))
    row = cur.fetchone()
    if row:
        return str(row[0])

    legacy_email = "dev@faircrm.local"
    if DEV_EMAIL != legacy_email:
        cur.execute("SELECT id FROM identity_users WHERE email = %s LIMIT 1", (legacy_email,))
        legacy = cur.fetchone()
        if legacy:
            user_id = str(legacy[0])
            cur.execute(
                "UPDATE identity_users SET email = %s, updated_at = %s WHERE id = %s",
                (DEV_EMAIL, _now(), user_id),
            )
            print(f"Updated dev user email: {legacy_email} -> {DEV_EMAIL}")
            return user_id

    user_id = str(uuid.uuid4())
    password_hash = PasswordHasher().hash(DEV_PASSWORD)
    now = _now()
    cur.execute(
        """
        INSERT INTO identity_users (
            id, email, password_hash, status, is_super_admin, created_at, updated_at, deleted_at
        ) VALUES (%s, %s, %s, 'active', FALSE, %s, %s, NULL)
        """,
        (user_id, DEV_EMAIL, password_hash, now, now),
    )
    print(f"Created dev user: {DEV_EMAIL}")
    return user_id


def grant_permissions_to_owner(cur, owner_role_id: str, codes: tuple[str, ...], label: str) -> None:
    for code in codes:
        cur.execute("SELECT id FROM identity_permissions WHERE code = %s LIMIT 1", (code,))
        perm = cur.fetchone()
        if perm is None:
            print(f"WARNING: permission missing (run Core migrations): {code}")
            continue
        cur.execute(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (owner_role_id, str(perm[0])),
        )
    print(f"Granted {label} permissions to owner role")


def main() -> int:
    admin_url = os.environ.get(
        "POSTGRES_ADMIN_URL",
        "postgresql://postgres:postgres@localhost:5432/postgres",
    )
    ensure_database_exists(admin_url, "kyrox_core")

    conn = _connect(CORE_DB_URL)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            roles = ensure_system_roles(cur)
            user_id = ensure_dev_user(cur)
            grant_permissions_to_owner(cur, roles["owner"], FAIR_CRM_PERMISSIONS, "fair_crm.customers.*")
            grant_permissions_to_owner(cur, roles["owner"], (AUDIT_READ_PERMISSION,), "audit.logs.read")
        conn.commit()
    except Exception as exc:
        conn.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()

    state = {
        "email": DEV_EMAIL,
        "password": DEV_PASSWORD,
        "user_id": user_id,
        "owner_role_id": roles["owner"],
    }
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"Wrote dev state to {STATE_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

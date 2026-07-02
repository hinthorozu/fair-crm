#!/usr/bin/env python3
"""Reset Fair CRM domain tables for development legacy migration (NOT for production)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND / ".env")

ALLOWED_ENVS = frozenset({"development", "local", "test"})
DEV_ORG_ID = UUID(
    os.environ.get("FAIR_CRM_DEV_ORGANIZATION_ID", "00000000-0000-4000-8000-000000000010")
)

DOMAIN_TABLES = (
    "crm_activities",
    "crm_customer_fair_participations",
    "crm_contacts",
    "crm_import_rows",
    "crm_import_batches",
    "crm_customers",
    "crm_fairs",
)


def _ensure_dev_only() -> None:
    app_env = os.environ.get("APP_ENV", "development").strip().lower()
    if app_env not in ALLOWED_ENVS:
        print(
            f"Refusing to reset: APP_ENV={app_env!r}. Allowed: {', '.join(sorted(ALLOWED_ENVS))}",
            file=sys.stderr,
        )
        raise SystemExit(1)


def count_domain_rows(db, org_id: UUID) -> dict[str, int]:
    from sqlalchemy import text

    counts: dict[str, int] = {}
    for table in DOMAIN_TABLES:
        if table in {"crm_import_rows", "crm_import_batches"}:
            result = db.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE organization_id = :org_id"),
                {"org_id": str(org_id)},
            )
        else:
            result = db.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE organization_id = :org_id"),
                {"org_id": str(org_id)},
            )
        counts[table] = int(result.scalar() or 0)
    return counts


def reset_domain_data(db, org_id: UUID) -> dict[str, int]:
    from sqlalchemy import text

    before = count_domain_rows(db, org_id)
    delete_order = [
        "crm_activities",
        "crm_customer_fair_participations",
        "crm_contacts",
        "crm_import_rows",
        "crm_import_batches",
        "crm_customers",
        "crm_fairs",
    ]
    deleted: dict[str, int] = {}
    for table in delete_order:
        if table == "crm_import_rows":
            result = db.execute(
                text(
                    f"DELETE FROM {table} WHERE organization_id = :org_id"
                ),
                {"org_id": str(org_id)},
            )
        else:
            result = db.execute(
                text(f"DELETE FROM {table} WHERE organization_id = :org_id"),
                {"org_id": str(org_id)},
            )
        deleted[table] = result.rowcount or 0

    after = count_domain_rows(db, org_id)
    return {"before": before, "deleted": deleted, "after": after}


def main() -> int:
    _ensure_dev_only()

    from app.core.config import get_settings
    from app.db.session import SessionLocal

    get_settings.cache_clear()
    settings = get_settings()
    if settings.app_env not in ALLOWED_ENVS:
        print(f"Refusing: backend APP_ENV={settings.app_env!r}", file=sys.stderr)
        return 1

    org_id = settings.dev_organization_id or DEV_ORG_ID
    db = SessionLocal()
    try:
        print(f"Organization: {org_id}")
        print("Counts before reset:")
        before = count_domain_rows(db, org_id)
        for table, count in before.items():
            print(f"  {table}: {count}")

        result = reset_domain_data(db, org_id)
        db.commit()

        print("\nDeleted rows:")
        for table, count in result["deleted"].items():
            print(f"  {table}: {count}")

        print("\nCounts after reset:")
        for table, count in result["after"].items():
            print(f"  {table}: {count}")
            if count != 0:
                print(f"WARNING: {table} is not empty after reset", file=sys.stderr)

        print("\nDomain reset complete.")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Reset failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

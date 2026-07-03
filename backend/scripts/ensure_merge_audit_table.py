"""Create merge audit log table when migration 0022 has not been applied yet."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    url = settings.database_url
    display_url = url
    if "@" in url and ":" in url.split("@")[0]:
        prefix, rest = url.split("@", 1)
        display_url = f"{prefix.rsplit(':', 1)[0]}:***@{rest}"

    print("DATABASE_URL", display_url)
    engine = create_engine(url)
    with engine.begin() as conn:
        db_name = conn.execute(text("SELECT current_database()")).scalar()
        alembic_version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        print("current_database", db_name)
        print("alembic_version_before", alembic_version)

        exists = conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'system_duplicate_group_merge_audit_logs'
                """
            )
        ).fetchone()
        if exists:
            print("system_duplicate_group_merge_audit_logs already exists")
            return

        conn.execute(
            text(
                """
                CREATE TABLE system_duplicate_group_merge_audit_logs (
                    id UUID PRIMARY KEY,
                    organization_id UUID NOT NULL,
                    executed_at TIMESTAMPTZ NOT NULL,
                    executed_by_user_id UUID NOT NULL,
                    executed_by_user_email VARCHAR(255),
                    run_id UUID NOT NULL,
                    group_key VARCHAR(512) NOT NULL,
                    group_by VARCHAR(32) NOT NULL,
                    surviving_customer_id UUID NOT NULL,
                    archived_customer_ids JSON NOT NULL,
                    scalar_field_sources JSON NOT NULL,
                    selected_email_ids JSON NOT NULL,
                    selected_phone_ids JSON NOT NULL,
                    selected_website_ids JSON NOT NULL,
                    statistics JSON NOT NULL,
                    reconstruction_json JSON NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX ix_system_dg_merge_audit_org_executed_at
                ON system_duplicate_group_merge_audit_logs (organization_id, executed_at)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX ix_system_duplicate_group_merge_audit_logs_organization_id
                ON system_duplicate_group_merge_audit_logs (organization_id)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX ix_system_duplicate_group_merge_audit_logs_executed_at
                ON system_duplicate_group_merge_audit_logs (executed_at)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX ix_system_duplicate_group_merge_audit_logs_executed_by_user_id
                ON system_duplicate_group_merge_audit_logs (executed_by_user_id)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX ix_system_duplicate_group_merge_audit_logs_run_id
                ON system_duplicate_group_merge_audit_logs (run_id)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX ix_system_duplicate_group_merge_audit_logs_surviving_customer_id
                ON system_duplicate_group_merge_audit_logs (surviving_customer_id)
                """
            )
        )
        print("created system_duplicate_group_merge_audit_logs")

    with engine.connect() as conn:
        exists = conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'system_duplicate_group_merge_audit_logs'
                """
            )
        ).fetchone()
        print("audit_table_exists_after", bool(exists))
        print("alembic_version_after", conn.execute(text("SELECT version_num FROM alembic_version")).scalar())
        print("note", "Alembic remains at 0020 until 0021 backfill passes; audit table was created manually for 0022.")


if __name__ == "__main__":
    main()

"""Diagnose merge-execute database state for the active backend DATABASE_URL."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    url = settings.database_url
    # Mask password in output
    display_url = url
    if "@" in url and ":" in url.split("@")[0]:
        prefix, rest = url.split("@", 1)
        user_part = prefix.rsplit(":", 1)[0] + ":***"
        display_url = f"{user_part}@{rest}"

    print("DATABASE_URL", display_url)
    print("APP_ENV", settings.app_env)

    engine = create_engine(url)
    with engine.connect() as conn:
        db_name = conn.execute(text("SELECT current_database()")).scalar()
        print("current_database", db_name)

        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        print("alembic_version", version)

        exists = inspect(engine).has_table("system_duplicate_group_merge_audit_logs")
        print("audit_table_exists", exists)

        if exists:
            count = conn.execute(
                text("SELECT COUNT(*) FROM system_duplicate_group_merge_audit_logs")
            ).scalar()
            print("audit_row_count", count)

        medikal = conn.execute(
            text(
                """
                SELECT COUNT(DISTINCT c.id)
                FROM crm_customer_emails e
                JOIN crm_customers c ON c.id = e.customer_id
                WHERE lower(e.email) = 'info@3smedikal.com'
                  AND c.status != 'deleted'
                """
            )
        ).scalar()
        print("active_3s_medikal_customers", medikal)


if __name__ == "__main__":
    main()

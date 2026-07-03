"""Fix dataset row unique index for multi-group duplicate analysis.

Migration 0024 may be blocked when Alembic is behind (e.g. stuck at 0020).
This script applies only the index change required for email/phone/website
grouping where one customer can appear in multiple duplicate groups.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.core.config import get_settings

OLD_INDEX = "ix_system_data_operation_dataset_rows_run_entity"
NEW_INDEX = "ix_system_data_operation_dataset_rows_run_entity_group"


def _mask_url(url: str) -> str:
    if "@" in url and ":" in url.split("@")[0]:
        prefix, rest = url.split("@", 1)
        return f"{prefix.rsplit(':', 1)[0]}:***@{rest}"
    return url


def main() -> int:
    settings = get_settings()
    url = settings.database_url
    print("DATABASE_URL", _mask_url(url))

    engine = create_engine(url)
    with engine.begin() as conn:
        dialect = conn.dialect.name
        if dialect != "postgresql":
            print(f"Unsupported dialect for this repair script: {dialect}")
            return 1

        alembic_version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        print("alembic_version", alembic_version)

        indexes = {
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND tablename = 'system_data_operation_dataset_rows'
                    """
                )
            )
        }
        print("existing_indexes", sorted(indexes))

        if NEW_INDEX in indexes and OLD_INDEX not in indexes:
            print(f"{NEW_INDEX} already present; nothing to do")
            return 0

        if OLD_INDEX in indexes:
            print(f"Dropping old unique index {OLD_INDEX}")
            conn.execute(text(f'DROP INDEX IF EXISTS "{OLD_INDEX}"'))

        if NEW_INDEX not in indexes:
            print(f"Creating unique index {NEW_INDEX}")
            conn.execute(
                text(
                    f"""
                    CREATE UNIQUE INDEX IF NOT EXISTS {NEW_INDEX}
                    ON system_data_operation_dataset_rows (
                        run_id,
                        entity_id,
                        group_by,
                        duplicate_group_key
                    )
                    """
                )
            )

        indexes_after = {
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND tablename = 'system_data_operation_dataset_rows'
                    """
                )
            )
        }
        print("indexes_after", sorted(indexes_after))

        if OLD_INDEX in indexes_after:
            print(f"ERROR: {OLD_INDEX} still present")
            return 1
        if NEW_INDEX not in indexes_after:
            print(f"ERROR: {NEW_INDEX} missing after repair")
            return 1

        print("Dataset row unique index repair completed successfully")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

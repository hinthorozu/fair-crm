"""Check migration 0021 blockers on active DATABASE_URL."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.core.config import get_settings


def main() -> None:
    engine = create_engine(get_settings().database_url)
    with engine.connect() as conn:
        phone = conn.execute(
            text(
                """
                SELECT count(*) FROM crm_customers c
                WHERE c.phone IS NOT NULL AND trim(c.phone) <> ''
                AND NOT EXISTS (
                    SELECT 1 FROM crm_customer_phones p
                    WHERE p.customer_id = c.id AND p.phone = c.phone
                )
                """
            )
        ).scalar()
        print("phone_mismatches", phone)
        cols = conn.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'crm_customers'
                  AND column_name IN ('phone', 'email', 'website')
                ORDER BY column_name
                """
            )
        ).fetchall()
        print("legacy_scalar_columns", [row[0] for row in cols])


if __name__ == "__main__":
    main()

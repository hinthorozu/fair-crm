"""Widen alembic_version.version_num so long revision IDs fit."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.core.config import get_settings


def main() -> int:
    engine = create_engine(get_settings().database_url)
    with engine.begin() as conn:
        current_len = conn.execute(
            text(
                """
                SELECT character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'alembic_version' AND column_name = 'version_num'
                """
            )
        ).scalar_one()
        print("current_version_num_length", current_len)
        if current_len is not None and current_len >= 128:
            print("already wide enough")
            return 0
        conn.execute(text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"))
        print("widened alembic_version.version_num to VARCHAR(128)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Keep alembic_version.version_num wide enough for long revision identifiers."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

ALEMBIC_VERSION_NUM_WIDTH = 128


def ensure_alembic_version_column_width(connection: Connection) -> None:
    """Widen version_num when Alembic's default VARCHAR(32) is too small."""
    current_len = connection.execute(
        text(
            """
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'alembic_version'
              AND column_name = 'version_num'
            """
        )
    ).scalar()
    if current_len is None:
        return
    if current_len >= ALEMBIC_VERSION_NUM_WIDTH:
        return
    connection.execute(
        text(
            f"ALTER TABLE alembic_version "
            f"ALTER COLUMN version_num TYPE VARCHAR({ALEMBIC_VERSION_NUM_WIDTH})"
        )
    )

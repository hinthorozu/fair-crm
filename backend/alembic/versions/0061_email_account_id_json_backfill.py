"""Backfill JSON smtp_account_id → email_account_id (C2 cutover).

Revision ID: 0061_email_account_id_json_backfill
Revises: 0060_email_accounts_provider_aware
"""

from __future__ import annotations

import json
from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0061_email_account_id_json_backfill"
down_revision: Union[str, None] = "0060_email_accounts_provider_aware"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_KEY = "smtp_account_id"
_NEW_KEY = "email_account_id"


def _as_dict(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return dict(parsed) if isinstance(parsed, dict) else None
    return None


def _migrate_dict(payload: dict[str, Any], *, reverse: bool = False) -> dict[str, Any] | None:
    """Copy old→new (or reverse) when target missing, then drop source key."""
    src, dst = (_NEW_KEY, _OLD_KEY) if reverse else (_OLD_KEY, _NEW_KEY)
    if src not in payload:
        return None
    updated = dict(payload)
    if dst not in updated:
        updated[dst] = updated[src]
    updated.pop(src, None)
    return updated


def _column_exists(bind, table: str, column: str) -> bool:
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return False
    return any(col["name"] == column for col in inspector.get_columns(table))


def _backfill_postgres(bind, table: str, column: str, *, reverse: bool = False) -> None:
    src, dst = (_NEW_KEY, _OLD_KEY) if reverse else (_OLD_KEY, _NEW_KEY)
    # Prefer jsonb: copy when dst missing, then remove src.
    bind.execute(
        sa.text(
            f"""
            UPDATE {table}
            SET {column} = (
                ({column}::jsonb - :src_key)
                || jsonb_build_object(
                    :dst_key,
                    COALESCE({column}::jsonb -> :dst_key, {column}::jsonb -> :src_key)
                )
            )
            WHERE {column} IS NOT NULL
              AND ({column}::jsonb) ? :src_key
            """
        ),
        {"src_key": src, "dst_key": dst},
    )


def _backfill_python(bind, table: str, column: str, pk: str = "id", *, reverse: bool = False) -> None:
    tbl = sa.table(table, sa.column(pk, sa.Uuid()), sa.column(column, sa.JSON()))
    rows = bind.execute(sa.select(tbl.c[pk], tbl.c[column]))
    for row in rows:
        payload = _as_dict(getattr(row, column))
        if not payload:
            continue
        updated = _migrate_dict(payload, reverse=reverse)
        if updated is None:
            continue
        bind.execute(tbl.update().where(tbl.c[pk] == getattr(row, pk)).values(**{column: updated}))


def _backfill_column(table: str, column: str, *, reverse: bool = False) -> None:
    bind = op.get_bind()
    if not _column_exists(bind, table, column):
        return
    if bind.dialect.name == "postgresql":
        _backfill_postgres(bind, table, column, reverse=reverse)
    else:
        _backfill_python(bind, table, column, reverse=reverse)


def upgrade() -> None:
    _backfill_column("crm_operations", "type_config")
    _backfill_column("mail_send_operations", "metadata_json")
    _backfill_column("crm_activities", "metadata_json")


def downgrade() -> None:
    _backfill_column("crm_operations", "type_config", reverse=True)
    _backfill_column("mail_send_operations", "metadata_json", reverse=True)
    _backfill_column("crm_activities", "metadata_json", reverse=True)

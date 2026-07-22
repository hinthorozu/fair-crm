"""Normalize operation fair sources: drop multiple_fairs, canonicalize source_ids.

Revision ID: 0051_operations_fair_source_ids
Revises: 0050_crm_operations_engine
"""

from __future__ import annotations

import json
from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0051_operations_fair_source_ids"
down_revision: Union[str, None] = "0050_crm_operations_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def _normalize_config(source_kind: str, source_config: Any) -> tuple[str, dict[str, Any]]:
    config = _as_dict(source_config)
    kind = "fair" if source_kind == "multiple_fairs" else source_kind

    ids: list[str] = []
    raw_ids = config.get("source_ids")
    if isinstance(raw_ids, list):
        ids.extend(str(item) for item in raw_ids if item is not None)

    raw_fair_ids = config.get("fair_ids")
    if isinstance(raw_fair_ids, list):
        ids.extend(str(item) for item in raw_fair_ids if item is not None)

    fair_id = config.get("fair_id")
    if fair_id is not None:
        ids.append(str(fair_id))

    seen: set[str] = set()
    unique_ids: list[str] = []
    for item in ids:
        if item in seen:
            continue
        seen.add(item)
        unique_ids.append(item)

    config.pop("fair_id", None)
    config.pop("fair_ids", None)
    if kind == "fair":
        config["source_ids"] = unique_ids
    else:
        config.pop("source_ids", None)

    return kind, config


def upgrade() -> None:
    bind = op.get_bind()
    operations = sa.table(
        "crm_operations",
        sa.column("id", sa.Uuid()),
        sa.column("source_kind", sa.String()),
        sa.column("source_config", sa.JSON()),
    )
    rows = bind.execute(sa.select(operations.c.id, operations.c.source_kind, operations.c.source_config))
    for row in rows:
        kind, config = _normalize_config(row.source_kind, row.source_config)
        bind.execute(
            operations.update()
            .where(operations.c.id == row.id)
            .values(source_kind=kind, source_config=config)
        )


def downgrade() -> None:
    # Irreversible data reshape; schema unchanged.
    pass

"""Add capability columns to operation_types; backfill from registry values.

Revision ID: 0056_operation_types_capabilities
Revises: 0055_operation_types
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0056_operation_types_capabilities"
down_revision: Union[str, None] = "0055_operation_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Exact values from OPERATION_TYPE_DEFINITIONS / _placeholder_capabilities at migration time.
_CAPABILITY_BACKFILL: dict[str, dict[str, bool]] = {
    "scraper": {
        "supports_pause": False,
        "supports_resume": False,
        "supports_retry": True,
        "supports_schedule": False,
        "supports_items": True,
        "requires_worker": True,
        "execution_ready": True,
    },
    "email": {
        "supports_pause": False,
        "supports_resume": False,
        "supports_retry": False,
        "supports_schedule": True,
        "supports_items": True,
        "requires_worker": True,
        "execution_ready": False,
    },
    "bulk_email": {
        "supports_pause": False,
        "supports_resume": False,
        "supports_retry": False,
        "supports_schedule": True,
        "supports_items": True,
        "requires_worker": True,
        "execution_ready": False,
    },
    "enrichment": {
        "supports_pause": False,
        "supports_resume": False,
        "supports_retry": False,
        "supports_schedule": False,
        "supports_items": True,
        "requires_worker": True,
        "execution_ready": False,
    },
    "duplicate_check": {
        "supports_pause": False,
        "supports_resume": False,
        "supports_retry": False,
        "supports_schedule": False,
        "supports_items": True,
        "requires_worker": True,
        "execution_ready": False,
    },
    "data_cleanup": {
        "supports_pause": False,
        "supports_resume": False,
        "supports_retry": False,
        "supports_schedule": False,
        "supports_items": True,
        "requires_worker": True,
        "execution_ready": False,
    },
    "whatsapp": {
        "supports_pause": False,
        "supports_resume": False,
        "supports_retry": False,
        "supports_schedule": True,
        "supports_items": True,
        "requires_worker": True,
        "execution_ready": False,
    },
    "manual_task": {
        "supports_pause": False,
        "supports_resume": False,
        "supports_retry": False,
        "supports_schedule": True,
        "supports_items": False,
        "requires_worker": False,
        "execution_ready": True,
    },
    "reminder": {
        "supports_pause": False,
        "supports_resume": False,
        "supports_retry": False,
        "supports_schedule": True,
        "supports_items": True,
        "requires_worker": True,
        "execution_ready": False,
    },
}

_CAPABILITY_COLUMNS = (
    "supports_pause",
    "supports_resume",
    "supports_retry",
    "supports_schedule",
    "supports_items",
    "requires_worker",
    "execution_ready",
)


def upgrade() -> None:
    for column_name in _CAPABILITY_COLUMNS:
        op.add_column(
            "operation_types",
            sa.Column(
                column_name,
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    bind = op.get_bind()
    for key, caps in _CAPABILITY_BACKFILL.items():
        bind.execute(
            sa.text(
                """
                UPDATE operation_types
                SET
                    supports_pause = :supports_pause,
                    supports_resume = :supports_resume,
                    supports_retry = :supports_retry,
                    supports_schedule = :supports_schedule,
                    supports_items = :supports_items,
                    requires_worker = :requires_worker,
                    execution_ready = :execution_ready
                WHERE key = :key
                """
            ),
            {"key": key, **caps},
        )

    for column_name in _CAPABILITY_COLUMNS:
        op.alter_column("operation_types", column_name, server_default=None)


def downgrade() -> None:
    for column_name in reversed(_CAPABILITY_COLUMNS):
        op.drop_column("operation_types", column_name)

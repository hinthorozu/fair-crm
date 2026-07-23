"""Create operation_types catalog and seed canonical keys.

Revision ID: 0055_operation_types
Revises: 0054_activity_todo_completion_links
"""

from datetime import UTC, datetime
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

from app.modules.operations.application.operation_type_seed import CANONICAL_OPERATION_TYPES

revision: str = "0055_operation_types"
down_revision: Union[str, None] = "0054_activity_todo_completion_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operation_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_operation_types_key"),
    )
    op.create_index("ix_operation_types_key", "operation_types", ["key"])
    op.create_index("ix_operation_types_is_active", "operation_types", ["is_active"])
    op.create_index("ix_operation_types_sort_order", "operation_types", ["sort_order"])

    now = datetime.now(UTC)
    rows = [
        {
            "id": uuid4(),
            "key": key,
            "name": name,
            "is_active": True,
            "sort_order": sort_order,
            "created_at": now,
            "updated_at": now,
        }
        for key, name, sort_order, _caps in CANONICAL_OPERATION_TYPES
    ]
    operation_types = sa.table(
        "operation_types",
        sa.column("id", sa.Uuid()),
        sa.column("key", sa.String()),
        sa.column("name", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(operation_types, rows)


def downgrade() -> None:
    op.drop_index("ix_operation_types_sort_order", table_name="operation_types")
    op.drop_index("ix_operation_types_is_active", table_name="operation_types")
    op.drop_index("ix_operation_types_key", table_name="operation_types")
    op.drop_table("operation_types")

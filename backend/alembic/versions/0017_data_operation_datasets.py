"""Revision ID: 0017_data_operation_datasets
Revises: 0016_system_data_operation_runs
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017_data_operation_datasets"
down_revision: Union[str, None] = "0016_system_data_operation_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_data_operation_dataset_rows",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("entity_kind", sa.String(32), nullable=False, server_default="customer"),
        sa.Column("entity_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_system_data_operation_dataset_rows_run_entity",
        "system_data_operation_dataset_rows",
        ["run_id", "entity_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_system_data_operation_dataset_rows_run_entity",
        table_name="system_data_operation_dataset_rows",
    )
    op.drop_table("system_data_operation_dataset_rows")

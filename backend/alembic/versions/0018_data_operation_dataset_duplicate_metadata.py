"""Revision ID: 0018_do_dataset_dup_meta
Revises: 0017_data_operation_datasets
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018_do_dataset_dup_meta"
down_revision: Union[str, None] = "0017_data_operation_datasets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "system_data_operation_dataset_rows",
        sa.Column("duplicate_group_key", sa.String(32), nullable=True),
    )
    op.add_column(
        "system_data_operation_dataset_rows",
        sa.Column("match_score", sa.Integer(), nullable=True),
    )
    op.add_column(
        "system_data_operation_dataset_rows",
        sa.Column("duplicate_reason", sa.String(255), nullable=True),
    )
    op.add_column(
        "system_data_operation_dataset_rows",
        sa.Column("fair_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "system_data_operation_dataset_rows",
        sa.Column("first_fair_name", sa.String(255), nullable=True),
    )
    op.create_index(
        "ix_system_data_operation_dataset_rows_run_group",
        "system_data_operation_dataset_rows",
        ["run_id", "duplicate_group_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_system_data_operation_dataset_rows_run_group",
        table_name="system_data_operation_dataset_rows",
    )
    op.drop_column("system_data_operation_dataset_rows", "first_fair_name")
    op.drop_column("system_data_operation_dataset_rows", "fair_count")
    op.drop_column("system_data_operation_dataset_rows", "duplicate_reason")
    op.drop_column("system_data_operation_dataset_rows", "match_score")
    op.drop_column("system_data_operation_dataset_rows", "duplicate_group_key")

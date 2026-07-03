"""Allow duplicate dataset rows per customer across duplicate groups.

Revision ID: 0024_dataset_row_group_unique
Revises: 0023_crm_list_performance_indexes
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0024_dataset_row_group_unique"
down_revision: Union[str, None] = "0023_crm_list_performance_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_system_data_operation_dataset_rows_run_entity")
    op.create_index(
        "ix_system_data_operation_dataset_rows_run_entity_group",
        "system_data_operation_dataset_rows",
        ["run_id", "entity_id", "group_by", "duplicate_group_key"],
        unique=True,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_system_data_operation_dataset_rows_run_entity_group",
        table_name="system_data_operation_dataset_rows",
    )
    op.create_index(
        "ix_system_data_operation_dataset_rows_run_entity",
        "system_data_operation_dataset_rows",
        ["run_id", "entity_id"],
        unique=True,
    )

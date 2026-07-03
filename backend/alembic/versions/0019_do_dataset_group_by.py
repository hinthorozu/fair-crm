"""Revision ID: 0019_do_dataset_group_by
Revises: 0018_do_dataset_dup_meta
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019_do_dataset_group_by"
down_revision: Union[str, None] = "0018_do_dataset_dup_meta"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "system_data_operation_dataset_rows",
        sa.Column("group_by", sa.String(32), nullable=True),
    )
    op.alter_column(
        "system_data_operation_dataset_rows",
        "duplicate_group_key",
        existing_type=sa.String(32),
        type_=sa.String(512),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "system_data_operation_dataset_rows",
        "duplicate_group_key",
        existing_type=sa.String(512),
        type_=sa.String(32),
        existing_nullable=True,
    )
    op.drop_column("system_data_operation_dataset_rows", "group_by")

"""Add related_todo_id to crm_operations for manual_task → Todo link.

Revision ID: 0052_operations_related_todo_id
Revises: 0051_operations_fair_source_ids
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0052_operations_related_todo_id"
down_revision: Union[str, None] = "0051_operations_fair_source_ids"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "crm_operations",
        sa.Column("related_todo_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_crm_operations_related_todo_id",
        "crm_operations",
        ["related_todo_id"],
    )
    op.create_foreign_key(
        "fk_crm_operations_related_todo_id_crm_todos",
        "crm_operations",
        "crm_todos",
        ["related_todo_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_crm_operations_related_todo_id_crm_todos",
        "crm_operations",
        type_="foreignkey",
    )
    op.drop_index("ix_crm_operations_related_todo_id", table_name="crm_operations")
    op.drop_column("crm_operations", "related_todo_id")

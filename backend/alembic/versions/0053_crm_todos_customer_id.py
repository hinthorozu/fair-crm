"""Add optional customer_id to crm_todos.

Revision ID: 0053_crm_todos_customer_id
Revises: 0052_operations_related_todo_id
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0053_crm_todos_customer_id"
down_revision: Union[str, None] = "0052_operations_related_todo_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "crm_todos",
        sa.Column("customer_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_crm_todos_customer_id", "crm_todos", ["customer_id"])
    op.create_foreign_key(
        "fk_crm_todos_customer_id_crm_customers",
        "crm_todos",
        "crm_customers",
        ["customer_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_crm_todos_customer_id_crm_customers",
        "crm_todos",
        type_="foreignkey",
    )
    op.drop_index("ix_crm_todos_customer_id", table_name="crm_todos")
    op.drop_column("crm_todos", "customer_id")

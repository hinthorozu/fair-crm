"""Create crm_todos table.

Revision ID: 0043_crm_todos
Revises: 0041_fair_email_outbox_mail_operation_unique
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0043_crm_todos"
down_revision: Union[str, None] = "0041_fair_email_outbox_mail_operation_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_todos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="todo"),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="normal"),
        sa.Column("category", sa.String(length=32), nullable=False, server_default="genel_gorev"),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assignee_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_todos_organization_id", "crm_todos", ["organization_id"])
    op.create_index(
        "ix_crm_todos_organization_status",
        "crm_todos",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_crm_todos_organization_updated_at",
        "crm_todos",
        ["organization_id", "updated_at"],
    )
    op.create_index("ix_crm_todos_assignee_user_id", "crm_todos", ["assignee_user_id"])
    op.create_index("ix_crm_todos_created_by", "crm_todos", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_crm_todos_created_by", table_name="crm_todos")
    op.drop_index("ix_crm_todos_assignee_user_id", table_name="crm_todos")
    op.drop_index("ix_crm_todos_organization_updated_at", table_name="crm_todos")
    op.drop_index("ix_crm_todos_organization_status", table_name="crm_todos")
    op.drop_index("ix_crm_todos_organization_id", table_name="crm_todos")
    op.drop_table("crm_todos")

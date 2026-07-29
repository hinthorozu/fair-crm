"""Add crm_todo_steps checklist table.

Revision ID: 0068_crm_todo_steps
Revises: 0067_import_batch_analyzed_at
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0068_crm_todo_steps"
down_revision: Union[str, None] = "0067_import_batch_analyzed_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "crm_todo_steps" in inspector.get_table_names():
        return

    op.create_table(
        "crm_todo_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("todo_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["todo_id"], ["crm_todos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_todo_steps_organization_id", "crm_todo_steps", ["organization_id"])
    op.create_index("ix_crm_todo_steps_todo_id", "crm_todo_steps", ["todo_id"])
    op.create_index(
        "ix_crm_todo_steps_org_todo_sort",
        "crm_todo_steps",
        ["organization_id", "todo_id", "sort_order"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "crm_todo_steps" not in inspector.get_table_names():
        return
    op.drop_index("ix_crm_todo_steps_org_todo_sort", table_name="crm_todo_steps")
    op.drop_index("ix_crm_todo_steps_todo_id", table_name="crm_todo_steps")
    op.drop_index("ix_crm_todo_steps_organization_id", table_name="crm_todo_steps")
    op.drop_table("crm_todo_steps")

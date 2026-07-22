"""Activity nullable customer_id + todo_id + fair_id; task_completed support.

Revision ID: 0054_activity_todo_completion_links
Revises: 0053_crm_todos_customer_id
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0054_activity_todo_completion_links"
down_revision: Union[str, None] = "0053_crm_todos_customer_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "crm_activities",
        "customer_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )

    op.add_column(
        "crm_activities",
        sa.Column("todo_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_crm_activities_todo_id", "crm_activities", ["todo_id"])
    op.create_foreign_key(
        "fk_crm_activities_todo_id_crm_todos",
        "crm_activities",
        "crm_todos",
        ["todo_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_crm_activities_todo_task_completed",
        "crm_activities",
        ["organization_id", "todo_id"],
        unique=True,
        postgresql_where=sa.text(
            "todo_id IS NOT NULL AND activity_type = 'task_completed' AND deleted_at IS NULL"
        ),
        sqlite_where=sa.text(
            "todo_id IS NOT NULL AND activity_type = 'task_completed' AND deleted_at IS NULL"
        ),
    )

    op.add_column(
        "crm_activities",
        sa.Column("fair_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_crm_activities_fair_id", "crm_activities", ["fair_id"])
    op.create_foreign_key(
        "fk_crm_activities_fair_id_crm_fairs",
        "crm_activities",
        "crm_fairs",
        ["fair_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_crm_activities_fair_id_crm_fairs",
        "crm_activities",
        type_="foreignkey",
    )
    op.drop_index("ix_crm_activities_fair_id", table_name="crm_activities")
    op.drop_column("crm_activities", "fair_id")

    op.drop_index(
        "uq_crm_activities_todo_task_completed",
        table_name="crm_activities",
    )
    op.drop_constraint(
        "fk_crm_activities_todo_id_crm_todos",
        "crm_activities",
        type_="foreignkey",
    )
    op.drop_index("ix_crm_activities_todo_id", table_name="crm_activities")
    op.drop_column("crm_activities", "todo_id")

    # Only safe if no NULL customer_id rows remain.
    op.alter_column(
        "crm_activities",
        "customer_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )

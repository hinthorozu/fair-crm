"""Todo worklist foundation: source fair, outcomes, worklist states.

Revision ID: 0046_crm_todo_worklist_foundation
Revises: 0045_merge_enrichment_and_todos
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0046_crm_todo_worklist_foundation"
down_revision: Union[str, None] = "0045_merge_enrichment_and_todos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("crm_todos", sa.Column("source_fair_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_crm_todos_source_fair_id",
        "crm_todos",
        "crm_fairs",
        ["source_fair_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_crm_todos_organization_source_fair",
        "crm_todos",
        ["organization_id", "source_fair_id"],
    )

    op.create_table(
        "crm_todo_outcome_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("primary_worklist_status", sa.String(length=32), nullable=False),
        sa.Column("requires_action", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("marks_data_problem", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "code",
            name="uq_crm_todo_outcome_definitions_org_code",
        ),
    )
    op.create_index(
        "ix_crm_todo_outcome_definitions_organization_id",
        "crm_todo_outcome_definitions",
        ["organization_id"],
    )
    op.create_index(
        "ix_crm_todo_outcome_definitions_org_active_sort",
        "crm_todo_outcome_definitions",
        ["organization_id", "is_active", "sort_order"],
    )

    op.create_table(
        "crm_todo_worklist_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("todo_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("participation_id", sa.Uuid(), nullable=True),
        sa.Column("primary_status", sa.String(length=32), nullable=False),
        sa.Column("last_activity_id", sa.Uuid(), nullable=True),
        sa.Column("last_outcome_id", sa.Uuid(), nullable=True),
        sa.Column("follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_note_summary", sa.String(length=500), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("data_problem", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["todo_id"], ["crm_todos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["crm_customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["participation_id"],
            ["crm_customer_fair_participations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["last_activity_id"], ["crm_activities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["last_outcome_id"],
            ["crm_todo_outcome_definitions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "todo_id",
            "customer_id",
            name="uq_crm_todo_worklist_states_org_todo_customer",
        ),
    )
    op.create_index(
        "ix_crm_todo_worklist_states_organization_id",
        "crm_todo_worklist_states",
        ["organization_id"],
    )
    op.create_index(
        "ix_crm_todo_worklist_states_org_todo_status",
        "crm_todo_worklist_states",
        ["organization_id", "todo_id", "primary_status"],
    )
    op.create_index(
        "ix_crm_todo_worklist_states_org_todo_follow_up",
        "crm_todo_worklist_states",
        ["organization_id", "todo_id", "follow_up_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_crm_todo_worklist_states_org_todo_follow_up", table_name="crm_todo_worklist_states")
    op.drop_index("ix_crm_todo_worklist_states_org_todo_status", table_name="crm_todo_worklist_states")
    op.drop_index("ix_crm_todo_worklist_states_organization_id", table_name="crm_todo_worklist_states")
    op.drop_table("crm_todo_worklist_states")

    op.drop_index(
        "ix_crm_todo_outcome_definitions_org_active_sort",
        table_name="crm_todo_outcome_definitions",
    )
    op.drop_index(
        "ix_crm_todo_outcome_definitions_organization_id",
        table_name="crm_todo_outcome_definitions",
    )
    op.drop_table("crm_todo_outcome_definitions")

    op.drop_index("ix_crm_todos_organization_source_fair", table_name="crm_todos")
    op.drop_constraint("fk_crm_todos_source_fair_id", "crm_todos", type_="foreignkey")
    op.drop_column("crm_todos", "source_fair_id")

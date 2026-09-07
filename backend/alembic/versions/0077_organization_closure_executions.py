"""Add durable organization closure execution state.

Revision ID: 0077_organization_closure_executions
Revises: 0076_cost_catalog
"""

from alembic import op
import sqlalchemy as sa

revision = "0077_organization_closure_executions"
down_revision = "0076_cost_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crm_organization_closure_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_phase", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_session_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("failure_code", sa.String(length=128), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('in_progress', 'blocked')",
            name="ck_org_closure_execution_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_org_closure_execution_idempotency",
        ),
    )
    op.create_index(
        "ix_crm_organization_closure_executions_organization_id",
        "crm_organization_closure_executions",
        ["organization_id"],
    )
    op.create_index(
        "uq_org_closure_execution_open_org",
        "crm_organization_closure_executions",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("closed_at IS NULL"),
        sqlite_where=sa.text("closed_at IS NULL"),
    )

    op.create_table(
        "crm_organization_closure_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_session_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("phase", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["crm_organization_closure_executions.id"],
            name="fk_org_closure_event_execution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crm_organization_closure_events_execution_id",
        "crm_organization_closure_events",
        ["execution_id"],
    )
    op.create_index(
        "ix_crm_organization_closure_events_organization_id",
        "crm_organization_closure_events",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_crm_organization_closure_events_organization_id",
        table_name="crm_organization_closure_events",
    )
    op.drop_index(
        "ix_crm_organization_closure_events_execution_id",
        table_name="crm_organization_closure_events",
    )
    op.drop_table("crm_organization_closure_events")
    op.drop_index(
        "uq_org_closure_execution_open_org",
        table_name="crm_organization_closure_executions",
    )
    op.drop_index(
        "ix_crm_organization_closure_executions_organization_id",
        table_name="crm_organization_closure_executions",
    )
    op.drop_table("crm_organization_closure_executions")

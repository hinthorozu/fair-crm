"""Add durable OL08-03A closure export plan manifests.

Revision ID: 0078_closure_export_plans
Revises: 0077_organization_closure_executions
"""

from alembic import op
import sqlalchemy as sa

revision = "0078_closure_export_plans"
down_revision = "0077_organization_closure_executions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crm_organization_closure_export_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("closure_execution_id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("disposition", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("manifest_digest", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_session_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "disposition = 'required'",
            name="ck_org_closure_export_plan_disposition",
        ),
        sa.CheckConstraint(
            "status = 'planned'",
            name="ck_org_closure_export_plan_status",
        ),
        sa.ForeignKeyConstraint(
            ["closure_execution_id"],
            ["crm_organization_closure_executions.id"],
            name="fk_org_closure_export_plan_execution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "closure_execution_id",
            "schema_version",
            name="uq_org_closure_export_plan_execution_schema",
        ),
    )
    op.create_index(
        "ix_crm_organization_closure_export_plans_organization_id",
        "crm_organization_closure_export_plans",
        ["organization_id"],
    )
    op.create_index(
        "ix_crm_organization_closure_export_plans_closure_execution_id",
        "crm_organization_closure_export_plans",
        ["closure_execution_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_crm_organization_closure_export_plans_closure_execution_id",
        table_name="crm_organization_closure_export_plans",
    )
    op.drop_index(
        "ix_crm_organization_closure_export_plans_organization_id",
        table_name="crm_organization_closure_export_plans",
    )
    op.drop_table("crm_organization_closure_export_plans")

"""Add OL08-D product-data hard-delete evidence and detach credential parent FK.

Revision ID: 0082_closure_product_cleanup
Revises: 0081_closure_artifact_purge
"""

from alembic import op
import sqlalchemy as sa

revision = "0082_closure_product_cleanup"
down_revision = "0081_closure_artifact_purge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # OL08-D retains the non-secret email_account_id as evidence but must not retain
    # the live product row solely to satisfy the old restrictive evidence FK.
    op.drop_constraint(
        "fk_org_closure_credential_email_account",
        "crm_organization_closure_credential_dispositions",
        type_="foreignkey",
    )

    op.create_table(
        "crm_organization_closure_product_cleanup_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("closure_execution_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("suspension_episode_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("class_key", sa.String(length=96), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("before_count", sa.Integer(), nullable=True),
        sa.Column("deleted_count", sa.Integer(), nullable=True),
        sa.Column("remaining_count", sa.Integer(), nullable=True),
        sa.Column("failure_code", sa.String(length=128), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_session_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("action = 'hard_delete'", name="ck_org_closure_product_cleanup_action"),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'blocked')",
            name="ck_org_closure_product_cleanup_status",
        ),
        sa.ForeignKeyConstraint(
            ["closure_execution_id"],
            ["crm_organization_closure_executions.id"],
            name="fk_org_closure_product_cleanup_execution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "closure_execution_id",
            "policy_version",
            "class_key",
            name="uq_org_closure_product_cleanup_class",
        ),
    )
    op.create_index(
        "ix_closure_product_cleanup_org",
        "crm_organization_closure_product_cleanup_items",
        ["organization_id"],
    )
    op.create_index(
        "ix_closure_product_cleanup_exec",
        "crm_organization_closure_product_cleanup_items",
        ["closure_execution_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_closure_product_cleanup_exec",
        table_name="crm_organization_closure_product_cleanup_items",
    )
    op.drop_index(
        "ix_closure_product_cleanup_org",
        table_name="crm_organization_closure_product_cleanup_items",
    )
    op.drop_table("crm_organization_closure_product_cleanup_items")
    op.create_foreign_key(
        "fk_org_closure_credential_email_account",
        "crm_organization_closure_credential_dispositions",
        "email_accounts",
        ["email_account_id"],
        ["id"],
        ondelete="RESTRICT",
    )

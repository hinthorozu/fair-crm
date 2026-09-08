"""Add durable OL08-04A closure credential disposition evidence.

Revision ID: 0079_closure_credential_dispositions
Revises: 0078_closure_export_plans
"""

from alembic import op
import sqlalchemy as sa

revision = "0079_closure_credential_dispositions"
down_revision = "0078_closure_export_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crm_organization_closure_credential_dispositions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("closure_execution_id", sa.Uuid(), nullable=False),
        sa.Column("email_account_id", sa.Uuid(), nullable=False),
        sa.Column("account_type", sa.String(length=32), nullable=False),
        sa.Column("provider_key", sa.String(length=64), nullable=True),
        sa.Column("capability_class", sa.String(length=48), nullable=False),
        sa.Column("external_invalidation_state", sa.String(length=48), nullable=False),
        sa.Column("target_verification_state", sa.String(length=32), nullable=False),
        sa.Column("external_credential_id", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=48), nullable=False),
        sa.Column("signing_secret_retained", sa.Boolean(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("failure_code", sa.String(length=128), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_session_id", sa.Uuid(), nullable=False),
        sa.Column("outbound_disabled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("external_invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("send_secret_purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "capability_class IN ('supported_unidentifiable', 'operator_required', 'not_applicable')",
            name="ck_org_closure_credential_capability_class",
        ),
        sa.CheckConstraint(
            "external_invalidation_state IN ('blocked_supported_unidentifiable', 'operator_required', 'not_applicable', 'confirmed')",
            name="ck_org_closure_credential_external_state",
        ),
        sa.CheckConstraint(
            "target_verification_state IN ('missing', 'unverified', 'not_required')",
            name="ck_org_closure_credential_target_state",
        ),
        sa.CheckConstraint(
            "status IN ('outbound_disabled', 'operator_required', 'blocked_supported_unidentifiable', 'local_send_secrets_purged', 'receive_only_pending', 'disposition_complete')",
            name="ck_org_closure_credential_status",
        ),
        sa.ForeignKeyConstraint(
            ["closure_execution_id"],
            ["crm_organization_closure_executions.id"],
            name="fk_org_closure_credential_execution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["email_account_id"],
            ["email_accounts.id"],
            name="fk_org_closure_credential_email_account",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "closure_execution_id",
            "email_account_id",
            name="uq_org_closure_credential_execution_account",
        ),
    )
    op.create_index(
        "ix_crm_organization_closure_credential_dispositions_organization_id",
        "crm_organization_closure_credential_dispositions",
        ["organization_id"],
    )
    op.create_index(
        "ix_crm_organization_closure_credential_dispositions_closure_execution_id",
        "crm_organization_closure_credential_dispositions",
        ["closure_execution_id"],
    )
    op.create_index(
        "ix_crm_organization_closure_credential_dispositions_email_account_id",
        "crm_organization_closure_credential_dispositions",
        ["email_account_id"],
    )

    op.create_table(
        "crm_organization_closure_credential_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("disposition_id", sa.Uuid(), nullable=False),
        sa.Column("closure_execution_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("email_account_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_session_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("from_status", sa.String(length=48), nullable=True),
        sa.Column("to_status", sa.String(length=48), nullable=False),
        sa.Column("evidence_code", sa.String(length=128), nullable=True),
        sa.Column("evidence_reference", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["disposition_id"],
            ["crm_organization_closure_credential_dispositions.id"],
            name="fk_org_closure_credential_event_disposition",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["closure_execution_id"],
            ["crm_organization_closure_executions.id"],
            name="fk_org_closure_credential_event_execution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crm_organization_closure_credential_events_disposition_id",
        "crm_organization_closure_credential_events",
        ["disposition_id"],
    )
    op.create_index(
        "ix_crm_organization_closure_credential_events_closure_execution_id",
        "crm_organization_closure_credential_events",
        ["closure_execution_id"],
    )
    op.create_index(
        "ix_crm_organization_closure_credential_events_organization_id",
        "crm_organization_closure_credential_events",
        ["organization_id"],
    )
    op.create_index(
        "ix_crm_organization_closure_credential_events_email_account_id",
        "crm_organization_closure_credential_events",
        ["email_account_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_crm_organization_closure_credential_events_email_account_id",
        table_name="crm_organization_closure_credential_events",
    )
    op.drop_index(
        "ix_crm_organization_closure_credential_events_organization_id",
        table_name="crm_organization_closure_credential_events",
    )
    op.drop_index(
        "ix_crm_organization_closure_credential_events_closure_execution_id",
        table_name="crm_organization_closure_credential_events",
    )
    op.drop_index(
        "ix_crm_organization_closure_credential_events_disposition_id",
        table_name="crm_organization_closure_credential_events",
    )
    op.drop_table("crm_organization_closure_credential_events")

    op.drop_index(
        "ix_crm_organization_closure_credential_dispositions_email_account_id",
        table_name="crm_organization_closure_credential_dispositions",
    )
    op.drop_index(
        "ix_crm_organization_closure_credential_dispositions_closure_execution_id",
        table_name="crm_organization_closure_credential_dispositions",
    )
    op.drop_index(
        "ix_crm_organization_closure_credential_dispositions_organization_id",
        table_name="crm_organization_closure_credential_dispositions",
    )
    op.drop_table("crm_organization_closure_credential_dispositions")

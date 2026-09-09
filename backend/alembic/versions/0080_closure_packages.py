"""Add durable OL08-E closure package and artifact inventory state.

Revision ID: 0080_closure_packages
Revises: 0079_closure_credential_dispositions
"""

from alembic import op
import sqlalchemy as sa

revision = "0080_closure_packages"
down_revision = "0079_closure_credential_dispositions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crm_organization_closure_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("closure_execution_id", sa.Uuid(), nullable=False),
        sa.Column("export_plan_id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("inventory_schema_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("storage_locator", sa.String(length=1024), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("manifest_digest", sa.String(length=64), nullable=False),
        sa.Column("package_digest", sa.String(length=64), nullable=True),
        sa.Column("byte_size", sa.BigInteger(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("failure_code", sa.String(length=128), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_session_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("integrity_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('planned', 'generating', 'ready', 'integrity_verified', 'expired', 'purged', 'blocked')",
            name="ck_org_closure_package_status",
        ),
        sa.ForeignKeyConstraint(
            ["closure_execution_id"],
            ["crm_organization_closure_executions.id"],
            name="fk_org_closure_package_execution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["export_plan_id"],
            ["crm_organization_closure_export_plans.id"],
            name="fk_org_closure_package_export_plan",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "closure_execution_id",
            "schema_version",
            name="uq_org_closure_package_execution_schema",
        ),
    )
    op.create_index(
        "ix_closure_package_org",
        "crm_organization_closure_packages",
        ["organization_id"],
    )
    op.create_index(
        "ix_closure_package_exec",
        "crm_organization_closure_packages",
        ["closure_execution_id"],
    )

    op.create_table(
        "crm_organization_closure_artifact_inventory",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), nullable=False),
        sa.Column("closure_execution_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_schema_version", sa.String(length=64), nullable=False),
        sa.Column("artifact_key", sa.String(length=512), nullable=False),
        sa.Column("artifact_class", sa.String(length=96), nullable=False),
        sa.Column("ownership_class", sa.String(length=48), nullable=False),
        sa.Column("owner_type", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.String(length=200), nullable=False),
        sa.Column("storage_kind", sa.String(length=48), nullable=False),
        sa.Column("package_disposition", sa.String(length=64), nullable=False),
        sa.Column("cleanup_action", sa.String(length=64), nullable=False),
        sa.Column("locator_json", sa.JSON(), nullable=False),
        sa.Column("package_entry", sa.String(length=1024), nullable=True),
        sa.Column("byte_size", sa.BigInteger(), nullable=True),
        sa.Column("content_digest", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "ownership_class IN ('managed_product_artifact', 'external_reference')",
            name="ck_org_closure_artifact_ownership_class",
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["crm_organization_closure_packages.id"],
            name="fk_org_closure_artifact_package",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["closure_execution_id"],
            ["crm_organization_closure_executions.id"],
            name="fk_org_closure_artifact_execution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "package_id",
            "artifact_key",
            name="uq_org_closure_artifact_package_key",
        ),
    )
    op.create_index(
        "ix_closure_artifact_package",
        "crm_organization_closure_artifact_inventory",
        ["package_id"],
    )
    op.create_index(
        "ix_closure_artifact_org",
        "crm_organization_closure_artifact_inventory",
        ["organization_id"],
    )
    op.create_index(
        "ix_closure_artifact_exec",
        "crm_organization_closure_artifact_inventory",
        ["closure_execution_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_closure_artifact_exec",
        table_name="crm_organization_closure_artifact_inventory",
    )
    op.drop_index(
        "ix_closure_artifact_org",
        table_name="crm_organization_closure_artifact_inventory",
    )
    op.drop_index(
        "ix_closure_artifact_package",
        table_name="crm_organization_closure_artifact_inventory",
    )
    op.drop_table("crm_organization_closure_artifact_inventory")

    op.drop_index(
        "ix_closure_package_exec",
        table_name="crm_organization_closure_packages",
    )
    op.drop_index(
        "ix_closure_package_org",
        table_name="crm_organization_closure_packages",
    )
    op.drop_table("crm_organization_closure_packages")

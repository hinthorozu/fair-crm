"""Add OL08-E closure package and artifact inventory foundation.

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
    op.add_column(
        "crm_organization_closure_executions",
        sa.Column("lifecycle_updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "crm_organization_closure_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("closure_execution_id", sa.Uuid(), nullable=False),
        sa.Column("export_plan_id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("package_locator", sa.String(length=512), nullable=True),
        sa.Column("package_sha256", sa.String(length=64), nullable=True),
        sa.Column("package_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("member_count", sa.Integer(), nullable=True),
        sa.Column("manifest_json", sa.JSON(), nullable=True),
        sa.Column("failure_code", sa.String(length=128), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_session_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("integrity_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('planned', 'generating', 'ready', 'integrity_verified', 'blocked', 'expired', 'purged')",
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
        unique=False,
    )
    op.create_index(
        "ix_closure_package_exec",
        "crm_organization_closure_packages",
        ["closure_execution_id"],
        unique=False,
    )

    op.create_table(
        "crm_organization_closure_artifact_inventory",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("closure_execution_id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("artifact_class", sa.String(length=96), nullable=False),
        sa.Column("owner_type", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("owner_field", sa.String(length=64), nullable=False),
        sa.Column("storage_class", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("package_included", sa.Boolean(), nullable=False),
        sa.Column("cleanup_action", sa.String(length=48), nullable=False),
        sa.Column("locator", sa.String(length=255), nullable=False),
        sa.Column("package_member", sa.String(length=512), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "storage_class IN ('managed_file', 'embedded_bytes', 'external_reference')",
            name="ck_org_closure_artifact_storage_class",
        ),
        sa.CheckConstraint(
            "status IN ('certified', 'external_reference')",
            name="ck_org_closure_artifact_status",
        ),
        sa.CheckConstraint(
            "cleanup_action IN ('delete_managed_file', 'delete_with_owner_row', 'retain_external_reference')",
            name="ck_org_closure_artifact_cleanup_action",
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
            "owner_type",
            "owner_id",
            "owner_field",
            "locator",
            name="uq_org_closure_artifact_owner_locator",
        ),
    )
    op.create_index(
        "ix_closure_artifact_org",
        "crm_organization_closure_artifact_inventory",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_closure_artifact_exec",
        "crm_organization_closure_artifact_inventory",
        ["closure_execution_id"],
        unique=False,
    )
    op.create_index(
        "ix_closure_artifact_package",
        "crm_organization_closure_artifact_inventory",
        ["package_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_closure_artifact_package",
        table_name="crm_organization_closure_artifact_inventory",
    )
    op.drop_index(
        "ix_closure_artifact_exec",
        table_name="crm_organization_closure_artifact_inventory",
    )
    op.drop_index(
        "ix_closure_artifact_org",
        table_name="crm_organization_closure_artifact_inventory",
    )
    op.drop_table("crm_organization_closure_artifact_inventory")
    op.drop_index("ix_closure_package_exec", table_name="crm_organization_closure_packages")
    op.drop_index("ix_closure_package_org", table_name="crm_organization_closure_packages")
    op.drop_table("crm_organization_closure_packages")
    op.drop_column("crm_organization_closure_executions", "lifecycle_updated_at")

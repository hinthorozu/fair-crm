"""Add strict OL08-E2 artifact/package purge evidence state.

Revision ID: 0081_closure_artifact_purge
Revises: 0080_closure_packages
"""

from alembic import op
import sqlalchemy as sa

revision = "0081_closure_artifact_purge"
down_revision = "0080_closure_packages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crm_organization_closure_packages",
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "crm_organization_closure_artifact_inventory",
        sa.Column(
            "cleanup_status",
            sa.String(length=48),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "crm_organization_closure_artifact_inventory",
        sa.Column(
            "cleanup_attempt_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "crm_organization_closure_artifact_inventory",
        sa.Column("cleanup_failure_code", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "crm_organization_closure_artifact_inventory",
        sa.Column("cleanup_failure_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "crm_organization_closure_artifact_inventory",
        sa.Column("cleanup_last_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "crm_organization_closure_artifact_inventory",
        sa.Column("nonexistence_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_org_closure_artifact_cleanup_status",
        "crm_organization_closure_artifact_inventory",
        "cleanup_status IN ('pending', 'not_applicable', 'relational_delete_required', 'purged', 'already_absent', 'blocked')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_org_closure_artifact_cleanup_status",
        "crm_organization_closure_artifact_inventory",
        type_="check",
    )
    op.drop_column(
        "crm_organization_closure_artifact_inventory",
        "nonexistence_verified_at",
    )
    op.drop_column(
        "crm_organization_closure_artifact_inventory",
        "cleanup_last_attempt_at",
    )
    op.drop_column(
        "crm_organization_closure_artifact_inventory",
        "cleanup_failure_message",
    )
    op.drop_column(
        "crm_organization_closure_artifact_inventory",
        "cleanup_failure_code",
    )
    op.drop_column(
        "crm_organization_closure_artifact_inventory",
        "cleanup_attempt_count",
    )
    op.drop_column(
        "crm_organization_closure_artifact_inventory",
        "cleanup_status",
    )
    op.drop_column("crm_organization_closure_packages", "purged_at")

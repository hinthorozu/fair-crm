"""Create Operation Engine tables.

Revision ID: 0050_crm_operations_engine
Revises: 0049_backup_restore_database_key
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0050_crm_operations_engine"
down_revision: Union[str, None] = "0049_backup_restore_database_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    op.create_table(
        "crm_operations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("operation_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("source_kind", sa.String(length=50), nullable=False),
        sa.Column("source_config", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("type_config", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("run_settings", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"),
        sa.Column("latest_run_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_operations_organization_id", "crm_operations", ["organization_id"])
    op.create_index("ix_crm_operations_operation_type", "crm_operations", ["operation_type"])
    op.create_index("ix_crm_operations_status", "crm_operations", ["status"])
    op.create_index(
        "ix_crm_operations_org_type_status",
        "crm_operations",
        ["organization_id", "operation_type", "status"],
    )

    op.create_table(
        "crm_operation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("succeeded_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_details", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("core_job_id", sa.Uuid(), nullable=True),
        sa.Column("triggered_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["operation_id"], ["crm_operations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crm_operation_runs_organization_id", "crm_operation_runs", ["organization_id"]
    )
    op.create_index("ix_crm_operation_runs_operation_id", "crm_operation_runs", ["operation_id"])
    op.create_index("ix_crm_operation_runs_status", "crm_operation_runs", ["status"])
    op.create_index("ix_crm_operation_runs_core_job_id", "crm_operation_runs", ["core_job_id"])
    op.create_index(
        "ix_crm_operation_runs_org_operation",
        "crm_operation_runs",
        ["organization_id", "operation_id"],
    )

    op.create_table(
        "crm_operation_run_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("item_key", sa.String(length=255), nullable=True),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("payload", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("result", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["crm_operation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["operation_id"], ["crm_operations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crm_operation_run_items_organization_id",
        "crm_operation_run_items",
        ["organization_id"],
    )
    op.create_index("ix_crm_operation_run_items_run_id", "crm_operation_run_items", ["run_id"])
    op.create_index(
        "ix_crm_operation_run_items_operation_id", "crm_operation_run_items", ["operation_id"]
    )
    op.create_index("ix_crm_operation_run_items_status", "crm_operation_run_items", ["status"])
    op.create_index("ix_crm_operation_run_items_item_key", "crm_operation_run_items", ["item_key"])
    op.create_index(
        "ix_crm_operation_run_items_target_id", "crm_operation_run_items", ["target_id"]
    )
    op.create_index(
        "ix_crm_operation_run_items_org_run_status",
        "crm_operation_run_items",
        ["organization_id", "run_id", "status"],
    )

    # silence unused bind warning for dialects that do not need it
    _ = bind


def downgrade() -> None:
    op.drop_index(
        "ix_crm_operation_run_items_org_run_status", table_name="crm_operation_run_items"
    )
    op.drop_index("ix_crm_operation_run_items_target_id", table_name="crm_operation_run_items")
    op.drop_index("ix_crm_operation_run_items_item_key", table_name="crm_operation_run_items")
    op.drop_index("ix_crm_operation_run_items_status", table_name="crm_operation_run_items")
    op.drop_index("ix_crm_operation_run_items_operation_id", table_name="crm_operation_run_items")
    op.drop_index("ix_crm_operation_run_items_run_id", table_name="crm_operation_run_items")
    op.drop_index(
        "ix_crm_operation_run_items_organization_id", table_name="crm_operation_run_items"
    )
    op.drop_table("crm_operation_run_items")

    op.drop_index("ix_crm_operation_runs_org_operation", table_name="crm_operation_runs")
    op.drop_index("ix_crm_operation_runs_core_job_id", table_name="crm_operation_runs")
    op.drop_index("ix_crm_operation_runs_status", table_name="crm_operation_runs")
    op.drop_index("ix_crm_operation_runs_operation_id", table_name="crm_operation_runs")
    op.drop_index("ix_crm_operation_runs_organization_id", table_name="crm_operation_runs")
    op.drop_table("crm_operation_runs")

    op.drop_index("ix_crm_operations_org_type_status", table_name="crm_operations")
    op.drop_index("ix_crm_operations_status", table_name="crm_operations")
    op.drop_index("ix_crm_operations_operation_type", table_name="crm_operations")
    op.drop_index("ix_crm_operations_organization_id", table_name="crm_operations")
    op.drop_table("crm_operations")

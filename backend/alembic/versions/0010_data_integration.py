"""Data Integration — header mode, jobs, templates (Sprint 09.1).

Revision ID: 0010_data_integration
Revises: 0009_list_indexes
Create Date: 2026-07-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_data_integration"
down_revision: Union[str, None] = "0009_list_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "crm_import_batches",
        sa.Column("header_mode", sa.String(32), nullable=True),
    )
    op.add_column(
        "crm_import_batches",
        sa.Column("header_row_index", sa.Integer(), nullable=True),
    )
    op.add_column(
        "crm_import_batches",
        sa.Column("selected_sheet_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "crm_import_batches",
        sa.Column("stored_file_content", sa.LargeBinary(), nullable=True),
    )

    op.create_table(
        "crm_import_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("crm_import_batches.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("job_type", sa.String(32), nullable=False, server_default="apply"),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("progress_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "crm_import_templates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False, server_default="excel"),
        sa.Column("header_mode", sa.String(32), nullable=True),
        sa.Column("header_row_index", sa.Integer(), nullable=True),
        sa.Column("mapping_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("crm_import_templates")
    op.drop_table("crm_import_jobs")
    op.drop_column("crm_import_batches", "stored_file_content")
    op.drop_column("crm_import_batches", "selected_sheet_name")
    op.drop_column("crm_import_batches", "header_row_index")
    op.drop_column("crm_import_batches", "header_mode")

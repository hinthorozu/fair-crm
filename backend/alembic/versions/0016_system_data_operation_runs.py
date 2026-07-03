"""Revision ID: 0016_system_data_operation_runs
Revises: 0015_import_batch_lifecycle
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016_system_data_operation_runs"
down_revision: Union[str, None] = "0015_import_batch_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_data_operation_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("operation_key", sa.String(64), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_by", sa.Uuid(), nullable=False),
        sa.Column("started_by_email", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("result", sa.String(16), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("stdout_text", sa.Text(), nullable=True),
        sa.Column("output_files_json", sa.JSON(), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_system_data_operation_runs_status",
        "system_data_operation_runs",
        ["status"],
    )
    op.create_index(
        "ix_system_data_operation_runs_started_at",
        "system_data_operation_runs",
        ["started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_system_data_operation_runs_started_at", table_name="system_data_operation_runs")
    op.drop_index("ix_system_data_operation_runs_status", table_name="system_data_operation_runs")
    op.drop_table("system_data_operation_runs")

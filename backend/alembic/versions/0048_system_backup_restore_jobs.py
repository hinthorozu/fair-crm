"""system backup restore jobs

Revision ID: 0048_system_backup_restore_jobs
Revises: 0047_merge_cancellation_and_todo_worklist
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0048_system_backup_restore_jobs"
down_revision: Union[str, None] = "0047_merge_cancellation_and_todo_worklist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_backup_restore_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("source_type", sa.String(32), nullable=False, index=True),
        sa.Column("backup_id", sa.Uuid(), nullable=True, index=True),
        sa.Column("uploaded_file_path", sa.Text(), nullable=True),
        sa.Column("source_file_name", sa.String(255), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, index=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_email", sa.String(255), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("restore_log_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_system_backup_restore_jobs_requested_at",
        "system_backup_restore_jobs",
        ["requested_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_system_backup_restore_jobs_requested_at", table_name="system_backup_restore_jobs")
    op.drop_table("system_backup_restore_jobs")

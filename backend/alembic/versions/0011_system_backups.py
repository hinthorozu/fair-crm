"""Revision ID: 0011_system_backups
Revises: 0010_data_integration
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_system_backups"
down_revision: Union[str, None] = "0010_data_integration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_backups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("progress_stage", sa.String(32), nullable=False, server_default="preparing"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_by_email", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_system_backups_status", "system_backups", ["status"])
    op.create_index("ix_system_backups_started_at", "system_backups", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_system_backups_started_at", table_name="system_backups")
    op.drop_index("ix_system_backups_status", table_name="system_backups")
    op.drop_table("system_backups")

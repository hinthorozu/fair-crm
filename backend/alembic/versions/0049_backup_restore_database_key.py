"""backup and restore job database keys

Revision ID: 0049_backup_restore_database_key
Revises: 0048_system_backup_restore_jobs
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0049_backup_restore_database_key"
down_revision: Union[str, None] = "0048_system_backup_restore_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "system_backups",
        sa.Column("database_key", sa.String(32), nullable=False, server_default="fair_crm"),
    )
    op.create_index("ix_system_backups_database_key", "system_backups", ["database_key"])
    op.alter_column("system_backups", "database_key", server_default=None)

    op.add_column(
        "system_backup_restore_jobs",
        sa.Column("source_database_key", sa.String(32), nullable=False, server_default="fair_crm"),
    )
    op.add_column(
        "system_backup_restore_jobs",
        sa.Column("target_database_key", sa.String(32), nullable=False, server_default="fair_crm"),
    )
    op.create_index(
        "ix_system_backup_restore_jobs_source_database_key",
        "system_backup_restore_jobs",
        ["source_database_key"],
    )
    op.create_index(
        "ix_system_backup_restore_jobs_target_database_key",
        "system_backup_restore_jobs",
        ["target_database_key"],
    )
    op.alter_column("system_backup_restore_jobs", "source_database_key", server_default=None)
    op.alter_column("system_backup_restore_jobs", "target_database_key", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_system_backup_restore_jobs_target_database_key", table_name="system_backup_restore_jobs")
    op.drop_index("ix_system_backup_restore_jobs_source_database_key", table_name="system_backup_restore_jobs")
    op.drop_column("system_backup_restore_jobs", "target_database_key")
    op.drop_column("system_backup_restore_jobs", "source_database_key")
    op.drop_index("ix_system_backups_database_key", table_name="system_backups")
    op.drop_column("system_backups", "database_key")

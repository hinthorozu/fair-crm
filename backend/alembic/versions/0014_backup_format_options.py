"""Add backup_format and manifest_json to system_backups."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_backup_format_options"
down_revision: Union[str, None] = "0013_import_row_customer_fks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "system_backups",
        sa.Column(
            "backup_format",
            sa.String(length=32),
            nullable=False,
            server_default="postgresql_dump",
        ),
    )
    op.add_column(
        "system_backups",
        sa.Column("manifest_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_system_backups_backup_format", "system_backups", ["backup_format"])
    op.alter_column("system_backups", "backup_format", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_system_backups_backup_format", table_name="system_backups")
    op.drop_column("system_backups", "manifest_json")
    op.drop_column("system_backups", "backup_format")

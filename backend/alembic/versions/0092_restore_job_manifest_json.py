"""Store optional restore table scope on restore jobs.

Revision ID: 0092_restore_job_manifest_json
Revises: 0091_fair_name_text
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0092_restore_job_manifest_json"
down_revision: Union[str, Sequence[str], None] = "0091_fair_name_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "system_backup_restore_jobs",
        sa.Column("manifest_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("system_backup_restore_jobs", "manifest_json")

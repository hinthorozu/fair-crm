"""Add adapter fields to crm_fairs.

Revision ID: 0027_crm_fairs_adapter_fields
Revises: 0026_scraper_run_log
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0027_crm_fairs_adapter_fields"
down_revision: Union[str, None] = "0026_scraper_run_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("crm_fairs", sa.Column("adapter_key", sa.String(length=100), nullable=True))
    op.add_column("crm_fairs", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("crm_fairs", sa.Column("scraper_config", sa.JSON(), nullable=True))
    op.create_index("ix_crm_fairs_adapter_key", "crm_fairs", ["adapter_key"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_crm_fairs_adapter_key", table_name="crm_fairs", if_exists=True)
    op.drop_column("crm_fairs", "scraper_config")
    op.drop_column("crm_fairs", "source_url")
    op.drop_column("crm_fairs", "adapter_key")

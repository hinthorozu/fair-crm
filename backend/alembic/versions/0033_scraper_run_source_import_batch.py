"""Add run_source and import_batch_id to scraper_run_history.

Revision ID: 0033_scraper_run_source_import_batch
Revises: 0032_crm_customer_social_urls
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0033_scraper_run_source_import_batch"
down_revision: Union[str, None] = "0032_crm_customer_social_urls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scraper_run_history",
        sa.Column("run_source", sa.String(length=32), nullable=False, server_default="manual_test"),
    )
    op.add_column(
        "scraper_run_history",
        sa.Column(
            "import_batch_id",
            sa.Uuid(),
            sa.ForeignKey("crm_import_batches.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_scraper_run_history_run_source", "scraper_run_history", ["run_source"])
    op.create_index("ix_scraper_run_history_import_batch_id", "scraper_run_history", ["import_batch_id"])

    op.execute(
        """
        UPDATE scraper_run_history
        SET run_source = 'fair_automation'
        WHERE fair_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_scraper_run_history_import_batch_id", table_name="scraper_run_history")
    op.drop_index("ix_scraper_run_history_run_source", table_name="scraper_run_history")
    op.drop_column("scraper_run_history", "import_batch_id")
    op.drop_column("scraper_run_history", "run_source")

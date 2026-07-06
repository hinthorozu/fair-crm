"""Add cooperative cancellation fields to scraper_run_history.

Revision ID: 0045_scraper_run_cancellation_fields
Revises: 0044_enrichment_candidate_query_indexes
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0045_scraper_run_cancellation_fields"
down_revision: Union[str, None] = "0044_enrichment_candidate_query_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scraper_run_history",
        sa.Column("cancel_requested_by", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "scraper_run_history",
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "scraper_run_history",
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "scraper_run_history",
        sa.Column("progress_current", sa.Integer(), nullable=True),
    )
    op.add_column(
        "scraper_run_history",
        sa.Column("progress_total", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_scraper_run_history_last_heartbeat_at",
        "scraper_run_history",
        ["last_heartbeat_at"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_scraper_run_history_last_heartbeat_at", table_name="scraper_run_history", if_exists=True)
    op.drop_column("scraper_run_history", "progress_total")
    op.drop_column("scraper_run_history", "progress_current")
    op.drop_column("scraper_run_history", "last_heartbeat_at")
    op.drop_column("scraper_run_history", "cancel_requested_at")
    op.drop_column("scraper_run_history", "cancel_requested_by")

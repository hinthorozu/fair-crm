"""Revision ID: 0025_scraper_run_history
Revises: 0024_dataset_row_group_unique
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0025_scraper_run_history"
down_revision: Union[str, None] = "0024_dataset_row_group_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scraper_run_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("adapter_key", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("input_url", sa.Text(), nullable=True),
        sa.Column("fair_name", sa.String(255), nullable=True),
        sa.Column("fair_year", sa.Integer(), nullable=True),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("website_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("email_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("phone_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("instagram_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("linkedin_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("facebook_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("youtube_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("x_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("output_json_path", sa.Text(), nullable=True),
        sa.Column("output_excel_path", sa.Text(), nullable=True),
    )
    op.create_index("ix_scraper_run_history_adapter_key", "scraper_run_history", ["adapter_key"])
    op.create_index("ix_scraper_run_history_status", "scraper_run_history", ["status"])
    op.create_index("ix_scraper_run_history_started_at", "scraper_run_history", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_scraper_run_history_started_at", table_name="scraper_run_history")
    op.drop_index("ix_scraper_run_history_status", table_name="scraper_run_history")
    op.drop_index("ix_scraper_run_history_adapter_key", table_name="scraper_run_history")
    op.drop_table("scraper_run_history")

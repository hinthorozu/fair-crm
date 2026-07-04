"""Revision ID: 0026_scraper_run_log
Revises: 0025_scraper_run_history
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0026_scraper_run_log"
down_revision: Union[str, None] = "0025_scraper_run_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scraper_run_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "run_id",
            sa.Uuid(),
            sa.ForeignKey("scraper_run_history.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("step", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
    )
    op.create_index("ix_scraper_run_log_run_id", "scraper_run_log", ["run_id"])
    op.create_index("ix_scraper_run_log_created_at", "scraper_run_log", ["created_at"])
    op.create_index("ix_scraper_run_log_run_id_created_at", "scraper_run_log", ["run_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_scraper_run_log_run_id_created_at", table_name="scraper_run_log")
    op.drop_index("ix_scraper_run_log_created_at", table_name="scraper_run_log")
    op.drop_index("ix_scraper_run_log_run_id", table_name="scraper_run_log")
    op.drop_table("scraper_run_log")

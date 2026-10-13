"""Reuse run history for globally exclusive system TOBB work."""
from alembic import op
import sqlalchemy as sa

revision = "0097_tobb_run_history"
down_revision = "0096_tobb_review_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scraper_run_history", sa.Column("requested_by", sa.Uuid(), nullable=True))
    op.add_column("scraper_run_history", sa.Column("summary_json", sa.JSON(), nullable=True))
    condition = sa.text("adapter_key = 'tobb_calendar' AND status IN ('queued', 'running', 'cancel_requested', 'cancelling')")
    op.create_index("uq_scraper_history_active_tobb", "scraper_run_history", ["adapter_key"], unique=True,
                    postgresql_where=condition, sqlite_where=condition)


def downgrade() -> None:
    op.drop_index("uq_scraper_history_active_tobb", table_name="scraper_run_history")
    op.drop_column("scraper_run_history", "summary_json")
    op.drop_column("scraper_run_history", "requested_by")

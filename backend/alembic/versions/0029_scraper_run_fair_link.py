"""Link scraper runs to fairs and organizations.

Revision ID: 0029_scraper_run_fair_link
Revises: 0028_scraper_adapters
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0029_scraper_run_fair_link"
down_revision: Union[str, None] = "0028_scraper_adapters"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scraper_run_history", sa.Column("organization_id", sa.Uuid(), nullable=True))
    op.add_column("scraper_run_history", sa.Column("fair_id", sa.Uuid(), nullable=True))
    op.create_index(
        "ix_scraper_run_history_organization_id",
        "scraper_run_history",
        ["organization_id"],
    )
    op.create_index(
        "ix_scraper_run_history_fair_id",
        "scraper_run_history",
        ["fair_id"],
    )
    op.create_foreign_key(
        "fk_scraper_run_history_fair_id",
        "scraper_run_history",
        "crm_fairs",
        ["fair_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_scraper_run_history_fair_id", "scraper_run_history", type_="foreignkey")
    op.drop_index("ix_scraper_run_history_fair_id", table_name="scraper_run_history")
    op.drop_index("ix_scraper_run_history_organization_id", table_name="scraper_run_history")
    op.drop_column("scraper_run_history", "fair_id")
    op.drop_column("scraper_run_history", "organization_id")

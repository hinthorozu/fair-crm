"""Add engine_key to scraper adapter instances.

Revision ID: 0031_scraper_adapter_engine_key
Revises: 0030_scraper_registry_adapter_hides
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0031_scraper_adapter_engine_key"
down_revision: Union[str, None] = "0030_scraper_registry_adapter_hides"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scraper_adapters",
        sa.Column("engine_key", sa.String(length=100), nullable=True),
    )
    op.execute(sa.text("UPDATE scraper_adapters SET engine_key = adapter_key WHERE engine_key IS NULL"))
    op.alter_column("scraper_adapters", "engine_key", nullable=False)
    op.create_index("ix_scraper_adapters_engine_key", "scraper_adapters", ["engine_key"])


def downgrade() -> None:
    op.drop_index("ix_scraper_adapters_engine_key", table_name="scraper_adapters")
    op.drop_column("scraper_adapters", "engine_key")

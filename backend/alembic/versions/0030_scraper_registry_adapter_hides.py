"""Hard-delete tombstones and add registry adapter hide table.

Revision ID: 0030_scraper_registry_adapter_hides
Revises: 0029_scraper_run_fair_link
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0030_scraper_registry_adapter_hides"
down_revision: Union[str, None] = "0029_scraper_run_fair_link"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("DELETE FROM scraper_adapters WHERE deleted_at IS NOT NULL"))

    op.create_table(
        "scraper_registry_adapter_hides",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("adapter_key", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "adapter_key",
            name="uq_scraper_registry_adapter_hides_org_key",
        ),
    )
    op.create_index(
        "ix_scraper_registry_adapter_hides_organization_id",
        "scraper_registry_adapter_hides",
        ["organization_id"],
    )
    op.create_index(
        "ix_scraper_registry_adapter_hides_adapter_key",
        "scraper_registry_adapter_hides",
        ["adapter_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_scraper_registry_adapter_hides_adapter_key", table_name="scraper_registry_adapter_hides")
    op.drop_index("ix_scraper_registry_adapter_hides_organization_id", table_name="scraper_registry_adapter_hides")
    op.drop_table("scraper_registry_adapter_hides")

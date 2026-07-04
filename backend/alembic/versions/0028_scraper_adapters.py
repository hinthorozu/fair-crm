"""Create scraper_adapters table.

Revision ID: 0028_scraper_adapters
Revises: 0027_crm_fairs_adapter_fields
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0028_scraper_adapters"
down_revision: Union[str, None] = "0027_crm_fairs_adapter_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scraper_adapters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("adapter_key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="experimental"),
        sa.Column("version", sa.String(length=50), nullable=True),
        sa.Column("manifest", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "adapter_key", name="uq_scraper_adapters_org_adapter_key"),
    )
    op.create_index("ix_scraper_adapters_organization_id", "scraper_adapters", ["organization_id"])
    op.create_index("ix_scraper_adapters_adapter_key", "scraper_adapters", ["adapter_key"])
    op.create_index("ix_scraper_adapters_status", "scraper_adapters", ["status"])
    op.create_index("ix_scraper_adapters_is_active", "scraper_adapters", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_scraper_adapters_is_active", table_name="scraper_adapters")
    op.drop_index("ix_scraper_adapters_status", table_name="scraper_adapters")
    op.drop_index("ix_scraper_adapters_adapter_key", table_name="scraper_adapters")
    op.drop_index("ix_scraper_adapters_organization_id", table_name="scraper_adapters")
    op.drop_table("scraper_adapters")

"""Add social media URL columns to crm_customers.

Revision ID: 0032_crm_customer_social_urls
Revises: 0031_scraper_adapter_engine_key
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0032_crm_customer_social_urls"
down_revision: Union[str, None] = "0031_scraper_adapter_engine_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SOCIAL_COLUMNS = (
    "instagram_url",
    "facebook_url",
    "linkedin_url",
    "youtube_url",
)


def upgrade() -> None:
    for column in _SOCIAL_COLUMNS:
        op.add_column(
            "crm_customers",
            sa.Column(column, sa.String(length=512), nullable=True),
        )


def downgrade() -> None:
    for column in reversed(_SOCIAL_COLUMNS):
        op.drop_column("crm_customers", column)

"""add quote price

Revision ID: 0074_quote_price
Revises: 0073_quotes
"""
from alembic import op
import sqlalchemy as sa

revision = "0074_quote_price"
down_revision = "0073_quotes"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("crm_quotes", sa.Column("price", sa.String(length=255), nullable=False, server_default=""))
    op.alter_column("crm_quotes", "price", server_default=None)


def downgrade():
    op.drop_column("crm_quotes", "price")

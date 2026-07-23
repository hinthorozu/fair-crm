"""Add fair_name to fair email outbox for multi-fair ops display/export.

Revision ID: 0059_fair_email_outbox_fair_name
Revises: 0058_fair_email_bulk_ops_nullable
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0059_fair_email_outbox_fair_name"
down_revision: Union[str, None] = "0058_fair_email_bulk_ops_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "crm_fair_email_outbox",
        sa.Column("fair_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("crm_fair_email_outbox", "fair_name")

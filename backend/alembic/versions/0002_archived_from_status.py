"""Add archived_from_status to crm_customers."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_archived_from_status"
down_revision: Union[str, None] = "0001_crm_customers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "crm_customers",
        sa.Column("archived_from_status", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("crm_customers", "archived_from_status")

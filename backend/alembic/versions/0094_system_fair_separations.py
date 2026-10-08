"""Record System Fairs a user kept as intentionally distinct.

Revision ID: 0094_system_fair_separations
Revises: 0093_system_fair_identity_name
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0094_system_fair_separations"
down_revision: Union[str, Sequence[str], None] = "0093_system_fair_identity_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_system_fair_separations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("identity_name", sa.String(length=500), nullable=False),
        sa.Column("city_key", sa.String(length=500), nullable=False),
        sa.Column("fair_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["fair_id"], ["crm_fairs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fair_id"),
    )
    op.create_index(
        "ix_crm_system_fair_separations_identity",
        "crm_system_fair_separations",
        ["source", "identity_name", "city_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_crm_system_fair_separations_identity",
        table_name="crm_system_fair_separations",
    )
    op.drop_table("crm_system_fair_separations")

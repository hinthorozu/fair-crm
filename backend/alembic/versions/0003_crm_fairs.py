"""Create crm_fairs table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_crm_fairs"
down_revision: Union[str, None] = "0002_archived_from_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_fairs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("organizer", sa.String(length=255), nullable=True),
        sa.Column("venue", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("normalized_name", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_from_status", sa.String(length=32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_fairs_organization_id", "crm_fairs", ["organization_id"])
    op.create_index("ix_crm_fairs_normalized_name", "crm_fairs", ["normalized_name"])
    op.create_index("ix_crm_fairs_status", "crm_fairs", ["status"])
    op.create_index(
        "ix_crm_fairs_org_created_id",
        "crm_fairs",
        ["organization_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_crm_fairs_org_created_id", table_name="crm_fairs")
    op.drop_index("ix_crm_fairs_status", table_name="crm_fairs")
    op.drop_index("ix_crm_fairs_normalized_name", table_name="crm_fairs")
    op.drop_index("ix_crm_fairs_organization_id", table_name="crm_fairs")
    op.drop_table("crm_fairs")

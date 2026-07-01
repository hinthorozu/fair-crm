"""Initial crm_customers table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_crm_customers"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("legal_name", sa.String(length=500), nullable=True),
        sa.Column("trade_name", sa.String(length=255), nullable=True),
        sa.Column("normalized_name", sa.String(length=500), nullable=False),
        sa.Column("customer_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("tax_number", sa.String(length=50), nullable=True),
        sa.Column("tax_office", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_customers_organization_id", "crm_customers", ["organization_id"])
    op.create_index("ix_crm_customers_normalized_name", "crm_customers", ["normalized_name"])
    op.create_index("ix_crm_customers_status", "crm_customers", ["status"])
    op.create_index(
        "ix_crm_customers_org_created_id",
        "crm_customers",
        ["organization_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_crm_customers_org_created_id", table_name="crm_customers")
    op.drop_index("ix_crm_customers_status", table_name="crm_customers")
    op.drop_index("ix_crm_customers_normalized_name", table_name="crm_customers")
    op.drop_index("ix_crm_customers_organization_id", table_name="crm_customers")
    op.drop_table("crm_customers")

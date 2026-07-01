"""crm_contacts table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_crm_contacts"
down_revision: Union[str, None] = "0003_crm_fairs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("mobile_phone", sa.String(length=50), nullable=True),
        sa.Column("linkedin", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["crm_customers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_contacts_organization_id", "crm_contacts", ["organization_id"])
    op.create_index("ix_crm_contacts_customer_id", "crm_contacts", ["customer_id"])
    op.create_index(
        "ix_crm_contacts_customer_primary",
        "crm_contacts",
        ["customer_id", "is_primary"],
    )


def downgrade() -> None:
    op.drop_index("ix_crm_contacts_customer_primary", table_name="crm_contacts")
    op.drop_index("ix_crm_contacts_customer_id", table_name="crm_contacts")
    op.drop_index("ix_crm_contacts_organization_id", table_name="crm_contacts")
    op.drop_table("crm_contacts")

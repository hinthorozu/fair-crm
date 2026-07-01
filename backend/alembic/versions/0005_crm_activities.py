"""crm_activities table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_crm_activities"
down_revision: Union[str, None] = "0004_crm_contacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("activity_type", sa.String(length=50), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("activity_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("follow_up_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="manual"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["crm_customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_activities_organization_id", "crm_activities", ["organization_id"])
    op.create_index("ix_crm_activities_customer_id", "crm_activities", ["customer_id"])
    op.create_index("ix_crm_activities_contact_id", "crm_activities", ["contact_id"])
    op.create_index(
        "ix_crm_activities_customer_activity_date",
        "crm_activities",
        ["customer_id", "activity_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_crm_activities_customer_activity_date", table_name="crm_activities")
    op.drop_index("ix_crm_activities_contact_id", table_name="crm_activities")
    op.drop_index("ix_crm_activities_customer_id", table_name="crm_activities")
    op.drop_index("ix_crm_activities_organization_id", table_name="crm_activities")
    op.drop_table("crm_activities")

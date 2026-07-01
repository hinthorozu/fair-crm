"""crm_customer_fair_participations table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_crm_participations"
down_revision: Union[str, None] = "0006_crm_imports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_customer_fair_participations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("fair_id", sa.Uuid(), nullable=False),
        sa.Column("hall", sa.String(length=100), nullable=True),
        sa.Column("stand", sa.String(length=100), nullable=True),
        sa.Column(
            "participation_status",
            sa.String(length=50),
            nullable=False,
            server_default="exhibitor",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("primary_contact_id", sa.Uuid(), nullable=True),
        sa.Column("visited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["crm_customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["fair_id"], ["crm_fairs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["primary_contact_id"], ["crm_contacts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crm_cfp_organization_id",
        "crm_customer_fair_participations",
        ["organization_id"],
    )
    op.create_index(
        "ix_crm_cfp_customer_id",
        "crm_customer_fair_participations",
        ["customer_id"],
    )
    op.create_index(
        "ix_crm_cfp_fair_id",
        "crm_customer_fair_participations",
        ["fair_id"],
    )
    op.create_index(
        "ix_crm_cfp_primary_contact_id",
        "crm_customer_fair_participations",
        ["primary_contact_id"],
    )
    op.create_index(
        "uq_crm_cfp_active_customer_fair",
        "crm_customer_fair_participations",
        ["organization_id", "customer_id", "fair_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_crm_cfp_active_customer_fair", table_name="crm_customer_fair_participations")
    op.drop_index("ix_crm_cfp_primary_contact_id", table_name="crm_customer_fair_participations")
    op.drop_index("ix_crm_cfp_fair_id", table_name="crm_customer_fair_participations")
    op.drop_index("ix_crm_cfp_customer_id", table_name="crm_customer_fair_participations")
    op.drop_index("ix_crm_cfp_organization_id", table_name="crm_customer_fair_participations")
    op.drop_table("crm_customer_fair_participations")

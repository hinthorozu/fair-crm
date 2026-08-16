"""Add organization-scoped cost catalog.

Revision ID: 0076_cost_catalog
Revises: 0075_all_foreign_keys_cascade
"""

from alembic import op
import sqlalchemy as sa

revision = "0076_cost_catalog"
down_revision = "0075_all_foreign_keys_cascade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crm_cost_categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "slug", name="uq_cost_category_org_slug"),
    )
    op.create_index("ix_crm_cost_categories_organization_id", "crm_cost_categories", ["organization_id"])

    op.create_table(
        "crm_cost_products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["crm_cost_categories.id"], name="fk_cost_product_category", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "slug", name="uq_cost_product_org_slug"),
    )
    op.create_index("ix_crm_cost_products_organization_id", "crm_cost_products", ["organization_id"])
    op.create_index("ix_crm_cost_products_category_id", "crm_cost_products", ["category_id"])


def downgrade() -> None:
    op.drop_index("ix_crm_cost_products_category_id", table_name="crm_cost_products")
    op.drop_index("ix_crm_cost_products_organization_id", table_name="crm_cost_products")
    op.drop_table("crm_cost_products")
    op.drop_index("ix_crm_cost_categories_organization_id", table_name="crm_cost_categories")
    op.drop_table("crm_cost_categories")

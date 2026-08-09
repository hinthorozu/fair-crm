"""task linked quotes

Revision ID: 0073_quotes
Revises: 0072_remove_template_content_body
"""
from alembic import op
import sqlalchemy as sa

revision = "0073_quotes"
down_revision = "0072_remove_template_content_body"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("crm_quotes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("todo_id", sa.Uuid(), sa.ForeignKey("crm_todos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.Uuid(), sa.ForeignKey("crm_customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("fair_id", sa.Uuid(), sa.ForeignKey("crm_fairs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("template_id", sa.Uuid(), sa.ForeignKey("crm_quote_templates.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quote_date", sa.Date(), nullable=False), sa.Column("status", sa.String(30), nullable=False),
        sa.Column("selected_items", sa.JSON(), nullable=False), sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "todo_id", name="uq_quote_org_todo"))
    op.create_index("ix_crm_quotes_organization_id", "crm_quotes", ["organization_id"])
    op.create_index("ix_crm_quotes_todo_id", "crm_quotes", ["todo_id"])
    op.create_index("ix_crm_quotes_customer_id", "crm_quotes", ["customer_id"])
    op.create_index("ix_crm_quotes_fair_id", "crm_quotes", ["fair_id"])


def downgrade():
    op.drop_table("crm_quotes")

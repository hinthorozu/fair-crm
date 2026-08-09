"""Add versioned quote templates.

Revision ID: 0070_quote_templates
Revises: 0069_unify_fair_email_outbox
"""
from alembic import op
import sqlalchemy as sa

revision = "0070_quote_templates"
down_revision = "0069_unify_fair_email_outbox"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("crm_quote_templates",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False), sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_crm_quote_templates_organization_id", "crm_quote_templates", ["organization_id"])
    op.create_table("crm_quote_template_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("template_id", sa.Uuid(), sa.ForeignKey("crm_quote_templates.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False), sa.Column("logo_url", sa.String(1024)),
        sa.Column("source_code", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid()), sa.UniqueConstraint("template_id", "version_number", name="uq_quote_template_version"))
    op.create_index("ix_crm_quote_template_versions_template_id", "crm_quote_template_versions", ["template_id"])
    op.create_foreign_key("fk_quote_templates_current_version", "crm_quote_templates", "crm_quote_template_versions", ["current_version_id"], ["id"], ondelete="RESTRICT")


def downgrade():
    op.drop_constraint("fk_quote_templates_current_version", "crm_quote_templates", type_="foreignkey")
    op.drop_table("crm_quote_template_versions")
    op.drop_table("crm_quote_templates")

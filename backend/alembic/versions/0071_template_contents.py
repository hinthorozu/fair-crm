"""Add template content tags and contents.

Revision ID: 0071_template_contents
Revises: 0070_quote_templates
"""
from alembic import op
import sqlalchemy as sa

revision = "0071_template_contents"
down_revision = "0070_quote_templates"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "crm_template_content_tags",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "name", name="uq_template_content_tag_org_name"),
    )
    op.create_index("ix_template_content_tags_organization_id", "crm_template_content_tags", ["organization_id"])
    op.create_table(
        "crm_template_contents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), sa.ForeignKey("crm_template_content_tags.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_template_contents_organization_id", "crm_template_contents", ["organization_id"])
    op.create_index("ix_template_contents_tag_id", "crm_template_contents", ["tag_id"])


def downgrade():
    op.drop_table("crm_template_contents")
    op.drop_table("crm_template_content_tags")

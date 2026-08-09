"""Remove unused template content body.

Revision ID: 0072_remove_template_content_body
Revises: 0071_template_contents
"""
from alembic import op
import sqlalchemy as sa

revision = "0072_remove_template_content_body"
down_revision = "0071_template_contents"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("crm_template_contents", "content")


def downgrade():
    op.add_column("crm_template_contents", sa.Column("content", sa.Text(), nullable=True))

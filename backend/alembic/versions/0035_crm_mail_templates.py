"""Create crm_mail_templates table.

Revision ID: 0035_crm_mail_templates
Revises: 0034_smtp_accounts
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0035_crm_mail_templates"
down_revision: Union[str, None] = "0034_smtp_accounts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_mail_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("template_type", sa.String(length=64), nullable=False, server_default="transactional"),
        sa.Column("language", sa.String(length=16), nullable=False, server_default="tr"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("variables_schema", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crm_mail_templates_organization_id",
        "crm_mail_templates",
        ["organization_id"],
    )
    op.create_index(
        "ix_crm_mail_templates_template_type",
        "crm_mail_templates",
        ["template_type"],
    )
    op.create_index(
        "ix_crm_mail_templates_language",
        "crm_mail_templates",
        ["language"],
    )
    op.create_index(
        "ix_crm_mail_templates_is_active",
        "crm_mail_templates",
        ["is_active"],
    )
    op.create_index(
        "uq_crm_mail_templates_org_key",
        "crm_mail_templates",
        ["organization_id", "key"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_crm_mail_templates_org_type_lang_default",
        "crm_mail_templates",
        ["organization_id", "template_type", "language"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND is_default = true"),
        sqlite_where=sa.text("deleted_at IS NULL AND is_default = 1"),
    )


def downgrade() -> None:
    op.drop_index("uq_crm_mail_templates_org_type_lang_default", table_name="crm_mail_templates")
    op.drop_index("uq_crm_mail_templates_org_key", table_name="crm_mail_templates")
    op.drop_index("ix_crm_mail_templates_is_active", table_name="crm_mail_templates")
    op.drop_index("ix_crm_mail_templates_language", table_name="crm_mail_templates")
    op.drop_index("ix_crm_mail_templates_template_type", table_name="crm_mail_templates")
    op.drop_index("ix_crm_mail_templates_organization_id", table_name="crm_mail_templates")
    op.drop_table("crm_mail_templates")

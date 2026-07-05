"""Create fair bulk email outbox tables.

Revision ID: 0036_crm_fair_email_outbox
Revises: 0035_crm_mail_templates
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0036_crm_fair_email_outbox"
down_revision: Union[str, None] = "0035_crm_mail_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_fair_email_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("fair_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("smtp_account_id", sa.Uuid(), nullable=True),
        sa.Column("subject_override", sa.Text(), nullable=True),
        sa.Column("recipient_options_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crm_fair_email_batches_organization_id",
        "crm_fair_email_batches",
        ["organization_id"],
    )
    op.create_index(
        "ix_crm_fair_email_batches_fair_id",
        "crm_fair_email_batches",
        ["fair_id"],
    )
    op.create_index(
        "ix_crm_fair_email_batches_status",
        "crm_fair_email_batches",
        ["status"],
    )

    op.create_table(
        "crm_fair_email_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("participation_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_name", sa.String(length=255), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("skip_reason", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("rendered_subject", sa.Text(), nullable=True),
        sa.Column("rendered_body_html", sa.Text(), nullable=True),
        sa.Column("rendered_body_text", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["crm_fair_email_batches.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_crm_fair_email_outbox_batch_id",
        "crm_fair_email_outbox",
        ["batch_id"],
    )
    op.create_index(
        "ix_crm_fair_email_outbox_organization_id",
        "crm_fair_email_outbox",
        ["organization_id"],
    )
    op.create_index(
        "ix_crm_fair_email_outbox_status",
        "crm_fair_email_outbox",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_crm_fair_email_outbox_status", table_name="crm_fair_email_outbox")
    op.drop_index("ix_crm_fair_email_outbox_organization_id", table_name="crm_fair_email_outbox")
    op.drop_index("ix_crm_fair_email_outbox_batch_id", table_name="crm_fair_email_outbox")
    op.drop_table("crm_fair_email_outbox")
    op.drop_index("ix_crm_fair_email_batches_status", table_name="crm_fair_email_batches")
    op.drop_index("ix_crm_fair_email_batches_fair_id", table_name="crm_fair_email_batches")
    op.drop_index("ix_crm_fair_email_batches_organization_id", table_name="crm_fair_email_batches")
    op.drop_table("crm_fair_email_batches")

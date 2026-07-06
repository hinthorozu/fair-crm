"""Add email/SMS consent fields to customers and contacts.

Revision ID: 0040_customer_contact_consent
Revises: 0039_fair_email_outbox_mail_send_operation_id
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0040_customer_contact_consent"
down_revision: Union[str, None] = "0039_fair_email_outbox_mail_send_operation_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("crm_customers", "crm_contacts"):
        op.add_column(
            table,
            sa.Column("email_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )
        op.add_column(
            table,
            sa.Column("sms_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )
        op.add_column(
            table,
            sa.Column("email_unsubscribed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.add_column(
            table,
            sa.Column("sms_unsubscribed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.add_column(
            table,
            sa.Column("consent_note", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    for table in ("crm_contacts", "crm_customers"):
        op.drop_column(table, "consent_note")
        op.drop_column(table, "sms_unsubscribed_at")
        op.drop_column(table, "email_unsubscribed_at")
        op.drop_column(table, "sms_allowed")
        op.drop_column(table, "email_allowed")

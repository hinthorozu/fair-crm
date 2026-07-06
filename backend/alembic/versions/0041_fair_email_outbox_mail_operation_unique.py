"""Unique mail_send_operation_id on fair email outbox.

Revision ID: 0041_fair_email_outbox_mail_operation_unique
Revises: 0040_customer_contact_consent
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0041_fair_email_outbox_mail_operation_unique"
down_revision: Union[str, None] = "0040_customer_contact_consent"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_crm_fair_email_outbox_mail_send_operation_id",
        "crm_fair_email_outbox",
        ["mail_send_operation_id"],
        unique=True,
        postgresql_where=sa.text("mail_send_operation_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_crm_fair_email_outbox_mail_send_operation_id",
        table_name="crm_fair_email_outbox",
    )

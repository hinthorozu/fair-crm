"""Add mail_send_operation_id to fair email outbox.

Revision ID: 0039_fair_email_outbox_mail_send_operation_id
Revises: 0038_mail_send_operations
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0039_fair_email_outbox_mail_send_operation_id"
down_revision: Union[str, None] = "0038_mail_send_operations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "crm_fair_email_outbox",
        sa.Column("mail_send_operation_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_crm_fair_email_outbox_mail_send_operation_id",
        "crm_fair_email_outbox",
        ["mail_send_operation_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_crm_fair_email_outbox_mail_send_operation_id",
        table_name="crm_fair_email_outbox",
    )
    op.drop_column("crm_fair_email_outbox", "mail_send_operation_id")

"""Add lookup index for MailerSend webhook MSO matching.

Revision ID: 0066_mail_send_external_message_id_idx
Revises: 0065_mail_send_operation_provider_result
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0066_mail_send_external_message_id_idx"
down_revision: Union[str, None] = "0065_mail_send_operation_provider_result"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "ix_mail_send_operations_email_account_external_message_id"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "mail_send_operations" not in inspector.get_table_names():
        return
    existing = {idx["name"] for idx in inspector.get_indexes("mail_send_operations")}
    if INDEX_NAME in existing:
        return
    op.create_index(
        INDEX_NAME,
        "mail_send_operations",
        ["email_account_id", "external_message_id"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "mail_send_operations" not in inspector.get_table_names():
        return
    existing = {idx["name"] for idx in inspector.get_indexes("mail_send_operations")}
    if INDEX_NAME in existing:
        op.drop_index(INDEX_NAME, table_name="mail_send_operations")

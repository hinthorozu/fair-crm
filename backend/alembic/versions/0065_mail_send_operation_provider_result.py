"""Add provider result fields to mail_send_operations.

Revision ID: 0065_mail_send_operation_provider_result
Revises: 0064_email_account_provider_configs
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0065_mail_send_operation_provider_result"
down_revision: Union[str, None] = "0064_email_account_provider_configs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "mail_send_operations" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("mail_send_operations")}
    if "external_message_id" not in existing:
        op.add_column(
            "mail_send_operations",
            sa.Column("external_message_id", sa.String(length=255), nullable=True),
        )
    if "provider_status" not in existing:
        op.add_column(
            "mail_send_operations",
            sa.Column("provider_status", sa.String(length=64), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "mail_send_operations" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("mail_send_operations")}
    if "provider_status" in existing:
        op.drop_column("mail_send_operations", "provider_status")
    if "external_message_id" in existing:
        op.drop_column("mail_send_operations", "external_message_id")

"""Create mail_send_operations table.

Revision ID: 0038_mail_send_operations
Revises: 0037_crm_activity_metadata_json
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0038_mail_send_operations"
down_revision: Union[str, None] = "0037_crm_activity_metadata_json"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mail_send_operations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("recipient_email", sa.String(length=320), nullable=False),
        sa.Column("recipient_name", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("smtp_account_id", sa.Uuid(), nullable=True),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("fair_id", sa.Uuid(), nullable=True),
        sa.Column("customer_id", sa.Uuid(), nullable=True),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retry_count", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("operation_logs", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sending_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mail_send_operations_organization_id", "mail_send_operations", ["organization_id"])
    op.create_index("ix_mail_send_operations_status", "mail_send_operations", ["status"])
    op.create_index(
        "ix_mail_send_operations_org_status_priority_created",
        "mail_send_operations",
        ["organization_id", "status", "priority", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_mail_send_operations_org_status_priority_created", table_name="mail_send_operations")
    op.drop_index("ix_mail_send_operations_status", table_name="mail_send_operations")
    op.drop_index("ix_mail_send_operations_organization_id", table_name="mail_send_operations")
    op.drop_table("mail_send_operations")

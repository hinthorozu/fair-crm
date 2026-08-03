"""Unify fair email outbox into mail_send_operations.

Revision ID: 0069_unify_fair_email_outbox
Revises: 0068_crm_todo_steps
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0069_unify_fair_email_outbox"
down_revision: Union[str, None] = "0068_crm_todo_steps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for column in (
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("participation_id", sa.Uuid(), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("recipient_source", sa.String(length=32), nullable=True),
        sa.Column("fair_name", sa.String(length=255), nullable=True),
        sa.Column("skip_reason", sa.String(length=255), nullable=True),
    ):
        op.add_column("mail_send_operations", column)

    # Existing paired records keep their central mail-operation id and receive
    # the CRM/fair context plus the most recent delivery state from outbox.
    op.execute(
        """
        UPDATE mail_send_operations AS m
        SET contact_id = o.contact_id,
            participation_id = o.participation_id,
            company_name = o.company_name,
            recipient_source = o.source,
            fair_name = o.fair_name,
            skip_reason = o.skip_reason,
            status = CASE WHEN o.status = 'pending' THEN 'queued' ELSE o.status END,
            subject = COALESCE(o.rendered_subject, m.subject),
            body_html = COALESCE(o.rendered_body_html, m.body_html),
            body_text = COALESCE(o.rendered_body_text, m.body_text),
            error_message = COALESCE(o.error_message, m.error_message),
            retry_count = GREATEST(COALESCE(o.send_attempt, 1), 1),
            sent_at = COALESCE(o.sent_at, m.sent_at),
            updated_at = GREATEST(o.updated_at, m.updated_at)
        FROM crm_fair_email_outbox AS o
        WHERE o.mail_send_operation_id = m.id
        """
    )

    # Preserve any historical outbox row that was never paired with a central
    # operation. Its outbox id becomes the unified operation id.
    op.execute(
        """
        INSERT INTO mail_send_operations (
            id, organization_id, source_type, status, priority,
            recipient_email, recipient_name, subject, body_html, body_text,
            email_account_id, template_id, fair_id, customer_id, contact_id,
            participation_id, batch_id, company_name, recipient_source,
            fair_name, skip_reason, retry_count, max_retry_count,
            error_message, operation_logs, metadata_json, queued_at, sent_at,
            created_at, updated_at
        )
        SELECT
            o.id, o.organization_id, 'fair_bulk_email',
            CASE WHEN o.status = 'pending' THEN 'queued' ELSE o.status END,
            99, o.email, o.recipient_name,
            COALESCE(o.rendered_subject, b.subject_override, 'Toplu e-posta'),
            o.rendered_body_html, o.rendered_body_text,
            b.email_account_id, b.template_id, b.fair_id, o.customer_id,
            o.contact_id, o.participation_id, o.batch_id, o.company_name,
            o.source, o.fair_name, o.skip_reason,
            GREATEST(COALESCE(o.send_attempt, 1), 1), 3,
            o.error_message, '[]'::json, '{}'::json,
            o.created_at, o.sent_at, o.created_at, o.updated_at
        FROM crm_fair_email_outbox AS o
        JOIN crm_fair_email_batches AS b ON b.id = o.batch_id
        WHERE o.mail_send_operation_id IS NULL
        """
    )

    op.create_index(
        "ix_mail_send_operations_batch_status",
        "mail_send_operations",
        ["batch_id", "status"],
        unique=False,
    )
    op.drop_table("crm_fair_email_outbox")


def downgrade() -> None:
    raise RuntimeError(
        "0069 merges two sources of truth and is intentionally irreversible; restore from backup instead."
    )

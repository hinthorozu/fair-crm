from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class MailSendOperationRecord:
    id: UUID
    organization_id: UUID
    source_type: str
    status: str
    priority: int
    recipient_email: str
    recipient_name: str | None
    subject: str
    body_html: str | None
    body_text: str | None
    smtp_account_id: UUID | None
    template_id: UUID | None
    fair_id: UUID | None
    customer_id: UUID | None
    batch_id: UUID | None
    retry_count: int
    max_retry_count: int
    error_code: str | None
    error_message: str | None
    operation_logs: list
    metadata_json: dict | None
    scheduled_at: datetime | None
    queued_at: datetime | None
    sending_started_at: datetime | None
    sent_at: datetime | None
    failed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime

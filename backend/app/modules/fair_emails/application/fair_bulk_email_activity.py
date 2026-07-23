from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.activities.domain.entities import Activity
from app.modules.activities.domain.value_objects import ActivitySource, ActivityStatus, ActivityType
from app.modules.activities.infrastructure.repositories.activity_repository import SqlAlchemyActivityRepository
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailOutboxModel
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import FairEmailBatchRecord

logger = logging.getLogger(__name__)

FAIR_BULK_EMAIL_METADATA_SOURCE = "fair_bulk_email"
SENSITIVE_ERROR_PATTERN = re.compile(
    r"(password|decrypt|secret|token|credential|api[_-]?key)",
    re.IGNORECASE,
)

RECIPIENT_SOURCE_NOTE_LABELS = {
    "customer": "müşteri",
    "contact": "yetkili kişi",
}


def sanitize_error_message(message: str | None) -> str | None:
    if message is None:
        return None
    cleaned = message.strip()
    if not cleaned:
        return None
    if SENSITIVE_ERROR_PATTERN.search(cleaned):
        return "Mail gönderimi sırasında bir hata oluştu."
    return cleaned[:1000]


def build_fair_bulk_email_activity_note(
    *,
    terminal_status: Literal["sent", "failed"],
    fair_name: str,
    template_name: str,
    subject: str,
    recipient_email: str,
    recipient_source: str,
    error_message: str | None = None,
) -> str:
    source_label = RECIPIENT_SOURCE_NOTE_LABELS.get(recipient_source, recipient_source)
    if terminal_status == "sent":
        return (
            f"Fuar toplu mail gönderildi. Fuar: {fair_name}. "
            f"Şablon: {template_name}. Konu: {subject}. "
            f"Alıcı: {recipient_email} ({source_label})."
        )
    safe_error = sanitize_error_message(error_message) or "Bilinmeyen hata"
    return (
        f"Fuar toplu mail gönderimi başarısız oldu. Fuar: {fair_name}. "
        f"Şablon: {template_name}. Konu: {subject}. "
        f"Alıcı: {recipient_email} ({source_label}). Hata: {safe_error}"
    )


def build_fair_bulk_email_activity_metadata(
    *,
    batch: FairEmailBatchRecord,
    outbox: FairEmailOutboxModel,
    fair_name: str,
    template_name: str,
    subject: str,
    terminal_status: Literal["sent", "failed"],
    error_message: str | None = None,
) -> dict[str, Any]:
    safe_error = sanitize_error_message(error_message)
    send_attempt = int(getattr(outbox, "send_attempt", None) or 1)
    metadata: dict[str, Any] = {
        "source": FAIR_BULK_EMAIL_METADATA_SOURCE,
        "fair_id": str(batch.fair_id) if batch.fair_id is not None else None,
        "fair_name": fair_name,
        "batch_id": str(batch.id),
        "outbox_id": str(outbox.id),
        "send_attempt": str(send_attempt),
        "template_id": str(batch.template_id),
        "template_name": template_name,
        "subject": subject,
        "recipient_email": outbox.email,
        "recipient_name": outbox.recipient_name,
        "recipient_source": outbox.source,
        "customer_id": str(outbox.customer_id) if outbox.customer_id is not None else None,
        "status": terminal_status,
    }
    if batch.smtp_account_id is not None:
        metadata["smtp_account_id"] = str(batch.smtp_account_id)
    if outbox.contact_id is not None:
        metadata["contact_id"] = str(outbox.contact_id)
    if safe_error:
        metadata["error_message"] = safe_error
    return metadata


def build_fair_bulk_email_activity_subject(terminal_status: Literal["sent", "failed"]) -> str:
    if terminal_status == "sent":
        return "Fuar toplu mail — Gönderildi"
    return "Fuar toplu mail — Başarısız"


def map_terminal_status_to_activity_status(terminal_status: Literal["sent", "failed"]) -> str:
    if terminal_status == "sent":
        return ActivityStatus.COMPLETED
    return ActivityStatus.CANCELLED


@dataclass(frozen=True)
class FairBulkEmailActivityContext:
    organization_id: UUID
    batch: FairEmailBatchRecord
    outbox: FairEmailOutboxModel
    fair_name: str
    template_name: str
    subject: str
    terminal_status: Literal["sent", "failed"]
    error_message: str | None = None
    activity_at: datetime | None = None


class FairBulkEmailActivityWriter:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._activity_repository = SqlAlchemyActivityRepository(session)

    def record_terminal_outbox(self, context: FairBulkEmailActivityContext) -> None:
        if context.outbox.status not in ("sent", "failed"):
            return
        if context.outbox.customer_id is None:
            # Manual/excel recipients have no CRM customer — skip activity entirely.
            return
        if context.outbox.organization_id != context.organization_id:
            logger.warning(
                "fair_bulk_email_activity_tenant_mismatch outbox_id=%s organization_id=%s",
                context.outbox.id,
                context.organization_id,
            )
            return

        send_attempt = int(getattr(context.outbox, "send_attempt", None) or 1)
        if self._activity_repository.exists_fair_bulk_email_outbox_attempt(
            context.organization_id,
            context.outbox.id,
            send_attempt,
        ):
            return

        terminal_status: Literal["sent", "failed"] = (
            "sent" if context.outbox.status == "sent" else "failed"
        )
        safe_error = sanitize_error_message(context.error_message or context.outbox.error_message)
        note = build_fair_bulk_email_activity_note(
            terminal_status=terminal_status,
            fair_name=context.fair_name,
            template_name=context.template_name,
            subject=context.subject,
            recipient_email=context.outbox.email,
            recipient_source=context.outbox.source,
            error_message=safe_error,
        )
        metadata = build_fair_bulk_email_activity_metadata(
            batch=context.batch,
            outbox=context.outbox,
            fair_name=context.fair_name,
            template_name=context.template_name,
            subject=context.subject,
            terminal_status=terminal_status,
            error_message=safe_error,
        )
        activity_at = context.activity_at or context.outbox.sent_at or context.outbox.updated_at
        activity = Activity.create(
            organization_id=context.organization_id,
            customer_id=context.outbox.customer_id,
            contact_id=context.outbox.contact_id if context.outbox.source == "contact" else None,
            activity_type=ActivityType.EMAIL,
            subject=build_fair_bulk_email_activity_subject(terminal_status),
            description=note,
            activity_date=activity_at,
            follow_up_date=None,
            status=map_terminal_status_to_activity_status(terminal_status),
            source=ActivitySource.EMAIL_AUTOMATION,
            is_active=True,
            now=activity_at,
            metadata_json=metadata,
        )
        self._activity_repository.add(activity)
        logger.info(
            "fair_bulk_email_activity_created outbox_id=%s customer_id=%s status=%s send_attempt=%s",
            context.outbox.id,
            context.outbox.customer_id,
            terminal_status,
            send_attempt,
        )

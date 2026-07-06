"""Sync fair bulk email outbox items with central mail_send_operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.fair_emails.infrastructure.persistence.models import FairEmailOutboxModel
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import FairEmailBatchRecord
from app.modules.fair_emails.domain.value_objects import ResolvedRecipient
from app.modules.mail_send_operations.application.mail_send_operation_service import MailSendOperationService
from app.modules.mail_send_operations.domain.value_objects import MailSendOperationStatus, MailSendSourceType
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
    SqlAlchemyMailSendOperationRepository,
)
from app.shared.consent import CONSENT_ERROR_CODE, CONSENT_SKIP_MESSAGES, CONSENT_SKIP_REASONS


class FairBulkEmailMailOperationSync:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._operation_repository = SqlAlchemyMailSendOperationRepository(session)
        self._mail_service = MailSendOperationService(self._operation_repository)

    def ensure_operations_for_batch(
        self,
        *,
        organization_id: UUID,
        batch: FairEmailBatchRecord,
        default_subject: str,
    ) -> None:
        outbox_items = (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.organization_id == organization_id,
                FairEmailOutboxModel.batch_id == batch.id,
            )
            .order_by(FairEmailOutboxModel.created_at.asc())
            .all()
        )
        for outbox in outbox_items:
            self._ensure_operation_for_outbox(
                organization_id=organization_id,
                batch=batch,
                outbox=outbox,
                default_subject=default_subject,
            )

    def create_skipped_operations_for_consent(
        self,
        *,
        organization_id: UUID,
        batch: FairEmailBatchRecord,
        default_subject: str,
        recipients: list[ResolvedRecipient],
    ) -> None:
        for recipient in recipients:
            if recipient.status != "skip" or recipient.skip_reason not in CONSENT_SKIP_REASONS:
                continue
            if not recipient.email:
                continue
            error_message = CONSENT_SKIP_MESSAGES.get(
                recipient.skip_reason or "",
                "Email consent disabled",
            )
            self._mail_service.create_consent_skipped_operation(
                CreateMailSendOperationParams(
                    organization_id=organization_id,
                    source_type=MailSendSourceType.FAIR_BULK_EMAIL,
                    recipient_email=recipient.email,
                    recipient_name=recipient.recipient_name or recipient.company_name,
                    subject=default_subject,
                    smtp_account_id=batch.smtp_account_id,
                    template_id=batch.template_id,
                    fair_id=batch.fair_id,
                    customer_id=recipient.customer_id,
                    batch_id=batch.id,
                    metadata_json={
                        "contact_id": str(recipient.contact_id) if recipient.contact_id else None,
                        "recipient_source": recipient.source,
                        "skip_reason": recipient.skip_reason,
                    },
                ),
                error_code=CONSENT_ERROR_CODE,
                error_message=error_message,
            )
        self._session.flush()

    def sync_outbox_sending(self, organization_id: UUID, outbox: FairEmailOutboxModel) -> None:
        operation_id = outbox.mail_send_operation_id
        if operation_id is None:
            return
        record = self._operation_repository.get_by_id(organization_id, operation_id)
        if record is None or record.status != MailSendOperationStatus.QUEUED:
            return
        self._mail_service.mark_sending(
            organization_id,
            operation_id,
            log_message="Fuar toplu mail gönderimi başladı",
        )

    def sync_outbox_sent(
        self,
        organization_id: UUID,
        outbox: FairEmailOutboxModel,
        *,
        subject: str,
        body_html: str | None,
        body_text: str | None,
    ) -> None:
        operation_id = outbox.mail_send_operation_id
        if operation_id is None:
            return
        record = self._operation_repository.get_by_id(organization_id, operation_id)
        if record is None or record.status == MailSendOperationStatus.SENT:
            return
        if record.status == MailSendOperationStatus.SENDING:
            self._operation_repository.update_rendered_content(
                organization_id,
                operation_id,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
            )
            self._mail_service.mark_sent(
                organization_id,
                operation_id,
                log_message="Fuar toplu mail gönderildi",
            )
            return
        if record.status == MailSendOperationStatus.QUEUED:
            self._mail_service.mark_sending(
                organization_id,
                operation_id,
                log_message="Fuar toplu mail gönderimi başladı",
            )
            self._operation_repository.update_rendered_content(
                organization_id,
                operation_id,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
            )
            self._mail_service.mark_sent(
                organization_id,
                operation_id,
                log_message="Fuar toplu mail gönderildi",
            )

    def sync_outbox_failed(
        self,
        organization_id: UUID,
        outbox: FairEmailOutboxModel,
        *,
        error_code: str | None,
        error_message: str,
    ) -> None:
        operation_id = outbox.mail_send_operation_id
        if operation_id is None:
            return
        record = self._operation_repository.get_by_id(organization_id, operation_id)
        if record is None or record.status in (
            MailSendOperationStatus.SENT,
            MailSendOperationStatus.FAILED,
        ):
            return
        if record.status == MailSendOperationStatus.QUEUED:
            self._mail_service.mark_failed(
                organization_id,
                operation_id,
                error_code=error_code,
                error_message=error_message,
                log_message=error_message,
            )
            return
        if record.status == MailSendOperationStatus.SENDING:
            self._mail_service.mark_failed(
                organization_id,
                operation_id,
                error_code=error_code,
                error_message=error_message,
                log_message=error_message,
            )

    def _ensure_operation_for_outbox(
        self,
        *,
        organization_id: UUID,
        batch: FairEmailBatchRecord,
        outbox: FairEmailOutboxModel,
        default_subject: str,
    ) -> None:
        if outbox.mail_send_operation_id is not None:
            return
        existing = self._operation_repository.find_fair_bulk_by_outbox_id(
            organization_id,
            outbox.id,
        )
        if existing is not None:
            outbox.mail_send_operation_id = existing.id
            self._session.flush()
            return
        operation = self._mail_service.create_mail_send_operation(
            CreateMailSendOperationParams(
                organization_id=organization_id,
                source_type=MailSendSourceType.FAIR_BULK_EMAIL,
                recipient_email=outbox.email,
                recipient_name=outbox.recipient_name or outbox.company_name,
                subject=default_subject,
                smtp_account_id=batch.smtp_account_id,
                template_id=batch.template_id,
                fair_id=batch.fair_id,
                customer_id=outbox.customer_id,
                batch_id=batch.id,
                metadata_json={
                    "outbox_id": str(outbox.id),
                    "contact_id": str(outbox.contact_id) if outbox.contact_id else None,
                    "recipient_source": outbox.source,
                },
            )
        )
        outbox.mail_send_operation_id = operation.id
        self._session.flush()

"""Dispatch queued mail send operations via the central EmailDeliveryService."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.email_delivery.application.email_delivery_service import EmailDeliveryService
from app.modules.email_delivery.domain.results import EmailDeliveryResult
from app.modules.fair_emails.application.fair_bulk_email_activity import (
    FairBulkEmailActivityContext,
    FairBulkEmailActivityWriter,
)
from app.modules.fair_emails.application.fair_bulk_mail_operation_sync import FairBulkEmailMailOperationSync
from app.modules.fair_emails.application.retry_fair_bulk_email_operation import (
    FairBulkEmailOperationRetryHandler,
)
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailOutboxModel
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    SqlAlchemyFairEmailBatchRepository,
)
from app.modules.mail_send_operations.domain.entities import MailSendOperationRecord
from app.modules.mail_send_operations.domain.value_objects import MailSendSourceType
from app.modules.mail_templates.infrastructure.repositories.mail_template_repository import (
    SqlAlchemyMailTemplateRepository,
)
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.shared.email_consent_policy import EmailConsentPolicy


class MailSendOperationDispatcher:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._batch_repository = SqlAlchemyFairEmailBatchRepository(session)
        self._template_repository = SqlAlchemyMailTemplateRepository(session)
        self._fair_bulk_handler = FairBulkEmailOperationRetryHandler(session)
        self._mail_operation_sync = FairBulkEmailMailOperationSync(session)
        self._activity_writer = FairBulkEmailActivityWriter(session)
        self._consent_policy = EmailConsentPolicy(session)
        self._delivery = EmailDeliveryService(session)

    def dispatch(self, operation: MailSendOperationRecord) -> EmailDeliveryResult:
        if operation.source_type == MailSendSourceType.FAIR_BULK_EMAIL:
            return self._dispatch_fair_bulk_email(operation)
        return self._dispatch_generic(operation)

    def record_fair_bulk_terminal_activity(
        self,
        operation: MailSendOperationRecord,
    ) -> None:
        """Write the CRM activity after a fair row reaches sent/failed."""
        if operation.source_type != MailSendSourceType.FAIR_BULK_EMAIL:
            return
        outbox = self._fair_bulk_handler.get_outbox_for_operation(
            operation.organization_id,
            operation.id,
        )
        if outbox is None or outbox.batch_id is None:
            return
        batch = self._fair_bulk_handler.get_batch(
            operation.organization_id,
            outbox.batch_id,
        )
        if batch is None:
            return
        self._record_fair_bulk_activity(
            organization_id=operation.organization_id,
            batch=batch,
            outbox_id=outbox.id,
            fair_id=batch.fair_id,
            template_id=batch.template_id,
            subject=outbox.rendered_subject or operation.subject,
        )

    def _dispatch_generic(self, operation: MailSendOperationRecord) -> EmailDeliveryResult:
        self._consent_policy.ensure_allowed_or_delivery_error(
            operation.organization_id,
            email=operation.recipient_email,
            customer_id=operation.customer_id,
        )
        if operation.email_account_id is None:
            raise SmtpMailDeliveryError(
                "Email account is required for mail delivery",
                error_type="MissingEmailAccount",
                retryable=False,
            )
        body_text = operation.body_text or operation.subject
        return self._delivery.send(
            organization_id=operation.organization_id,
            email_account_id=operation.email_account_id,
            to=operation.recipient_email,
            subject=operation.subject,
            body_text=body_text,
            body_html=operation.body_html,
        )

    def _dispatch_fair_bulk_email(self, operation: MailSendOperationRecord) -> EmailDeliveryResult:
        outbox = self._fair_bulk_handler.get_outbox_for_operation(
            operation.organization_id,
            operation.id,
        )
        if outbox is None:
            raise SmtpMailDeliveryError(
                "Linked fair bulk email outbox record not found",
                error_type="FairBulkOutboxNotFound",
            )

        batch_id = operation.batch_id or outbox.batch_id
        batch = self._fair_bulk_handler.get_batch(operation.organization_id, batch_id)
        if batch is None:
            raise SmtpMailDeliveryError(
                "Linked fair bulk email batch not found",
                error_type="FairBulkBatchNotFound",
            )

        self._fair_bulk_handler.validate_consent(operation.organization_id, outbox)
        if operation.email_account_id is None:
            raise SmtpMailDeliveryError(
                "Email account is required for mail delivery",
                error_type="MissingEmailAccount",
                retryable=False,
            )
        final_subject, body_text, body_html = self._fair_bulk_handler.build_send_payload(
            operation.organization_id,
            batch=batch,
            outbox=outbox,
        )

        self._batch_repository.mark_outbox_sending(
            operation.organization_id,
            batch.id,
            outbox.id,
        )
        delivery_result = self._delivery.send(
            organization_id=operation.organization_id,
            email_account_id=operation.email_account_id,
            to=operation.recipient_email or outbox.email,
            subject=final_subject,
            body_text=body_text,
            body_html=body_html,
        )
        external_message_id = (
            delivery_result.external_message_id
            if isinstance(delivery_result.external_message_id, str)
            else None
        )
        provider_status = (
            delivery_result.provider_status
            if isinstance(delivery_result.provider_status, str)
            else None
        )
        self._batch_repository.update_outbox_sent(
            operation.organization_id,
            batch.id,
            outbox.id,
            subject=final_subject,
            body_html=body_html,
            body_text=body_text,
            external_message_id=external_message_id,
            provider_status=provider_status,
        )
        self._record_fair_bulk_activity(
            organization_id=operation.organization_id,
            batch=batch,
            outbox_id=outbox.id,
            fair_id=batch.fair_id,
            template_id=batch.template_id,
            subject=final_subject,
            terminal_status="sent",
        )
        return delivery_result

    def _record_fair_bulk_activity(
        self,
        *,
        organization_id: UUID,
        batch,
        outbox_id: UUID,
        fair_id: UUID | None,
        template_id: UUID,
        subject: str,
        terminal_status: str | None = None,
    ) -> None:
        outbox = (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.id == outbox_id,
                FairEmailOutboxModel.organization_id == organization_id,
                FairEmailOutboxModel.batch_id == batch.id,
            )
            .one_or_none()
        )
        if outbox is None:
            return
        from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository

        fair_name = ""
        if fair_id is not None:
            fair = SqlAlchemyFairRepository(self._session).get_by_id(organization_id, fair_id)
            fair_name = fair.name if fair else ""
        template = self._template_repository.get_by_id(organization_id, template_id)
        template_name = template.name if template else ""
        try:
            self._activity_writer.record_terminal_outbox(
                FairBulkEmailActivityContext(
                    organization_id=organization_id,
                    batch=batch,
                    outbox=outbox,
                    fair_name=fair_name,
                    template_name=template_name,
                    subject=subject,
                    terminal_status=(
                        terminal_status
                        if terminal_status in ("sent", "failed")
                        else ("sent" if outbox.status == "sent" else "failed")
                    ),
                    error_message=outbox.error_message,
                )
            )
        except Exception:
            return

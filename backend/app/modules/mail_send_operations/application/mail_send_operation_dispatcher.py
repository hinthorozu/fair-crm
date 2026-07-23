"""Dispatch queued mail send operations to SMTP delivery."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

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
from app.modules.smtp.infrastructure.repositories.smtp_account_repository import SqlAlchemySmtpAccountRepository
from app.modules.smtp.infrastructure.smtp_mailer import send_smtp_message


class MailSendOperationDispatcher:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._smtp_repository = SqlAlchemySmtpAccountRepository(session)
        self._batch_repository = SqlAlchemyFairEmailBatchRepository(session)
        self._template_repository = SqlAlchemyMailTemplateRepository(session)
        self._fair_bulk_handler = FairBulkEmailOperationRetryHandler(session)
        self._mail_operation_sync = FairBulkEmailMailOperationSync(session)
        self._activity_writer = FairBulkEmailActivityWriter(session)

    def dispatch(self, operation: MailSendOperationRecord) -> None:
        if operation.source_type == MailSendSourceType.FAIR_BULK_EMAIL:
            self._dispatch_fair_bulk_email(operation)
            return
        self._dispatch_generic(operation)

    def _dispatch_generic(self, operation: MailSendOperationRecord) -> None:
        account = self._resolve_smtp_account(operation.organization_id, operation.smtp_account_id)
        body_text = operation.body_text or operation.subject
        send_smtp_message(
            account,
            recipient=operation.recipient_email,
            subject=operation.subject,
            body=body_text,
            body_html=operation.body_html,
        )

    def _dispatch_fair_bulk_email(self, operation: MailSendOperationRecord) -> None:
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
        account = self._resolve_smtp_account(operation.organization_id, operation.smtp_account_id)
        final_subject, body_text, body_html = self._fair_bulk_handler.build_send_payload(
            operation.organization_id,
            batch=batch,
            outbox=outbox,
        )

        self._batch_repository.mark_outbox_sending(outbox.id)
        send_smtp_message(
            account,
            recipient=operation.recipient_email or outbox.email,
            subject=final_subject,
            body=body_text,
            body_html=body_html,
        )
        self._batch_repository.update_outbox_sent(
            outbox.id,
            subject=final_subject,
            body_html=body_html,
            body_text=body_text,
        )
        self._record_fair_bulk_activity(
            organization_id=operation.organization_id,
            batch=batch,
            outbox_id=outbox.id,
            fair_id=batch.fair_id,
            template_id=batch.template_id,
            subject=final_subject,
        )

    def _resolve_smtp_account(self, organization_id: UUID, smtp_account_id: UUID | None):
        if smtp_account_id is None:
            raise SmtpMailDeliveryError(
                "SMTP account is required for mail delivery",
                error_type="MissingSmtpAccount",
            )
        account = self._smtp_repository.get_by_id(organization_id, smtp_account_id)
        if account is None or account.deleted_at is not None:
            raise SmtpMailDeliveryError(
                "SMTP account not found",
                error_type="SmtpAccountNotFound",
            )
        if not account.is_active:
            raise SmtpMailDeliveryError(
                "SMTP account is inactive",
                error_type="InactiveAccount",
            )
        return account

    def _record_fair_bulk_activity(
        self,
        *,
        organization_id: UUID,
        batch,
        outbox_id: UUID,
        fair_id: UUID | None,
        template_id: UUID,
        subject: str,
    ) -> None:
        outbox = (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.id == outbox_id,
                FairEmailOutboxModel.organization_id == organization_id,
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
                    terminal_status="sent" if outbox.status == "sent" else "failed",
                    error_message=outbox.error_message,
                )
            )
        except Exception:
            return

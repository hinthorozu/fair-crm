from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fair_emails.application.retry_fair_bulk_email_operation import (
    FairBulkEmailOperationRetryHandler,
)
from app.modules.mail_send_operations.application.commands import RetryMailSendOperationCommand
from app.modules.mail_send_operations.application.list_mail_send_operations import (
    MailSendOperationListItem,
    build_mail_send_operation_list_item,
)
from app.modules.mail_send_operations.application.mail_send_operation_service import MailSendOperationService
from app.modules.mail_send_operations.domain.exceptions import (
    InvalidMailSendOperationTransitionError,
    MailSendOperationNotFoundError,
    MailSendOperationRetryNotSupportedError,
)
from app.modules.mail_send_operations.domain.value_objects import (
    MailSendOperationStatus,
    MailSendSourceType,
)
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    SqlAlchemyMailSendOperationRepository,
)
from app.modules.mail_templates.domain.ports import MailTemplateRepository
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.smtp.domain.ports import SmtpAccountRepository
from app.modules.smtp.infrastructure.smtp_mailer import send_smtp_message
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.fairs.domain.ports import FairRepository

PERMISSION_UPDATE = "fair_crm.smtp.update"

RETRYABLE_SOURCE_TYPES = frozenset(
    {
        MailSendSourceType.SMTP_TEST,
        MailSendSourceType.TEMPLATE_TEST,
    }
)


@dataclass(frozen=True)
class RetryMailSendOperationResult:
    success: bool
    operation: MailSendOperationListItem


class RetryMailSendOperationUseCase:
    def __init__(
        self,
        repository: SqlAlchemyMailSendOperationRepository,
        mail_send_operations: MailSendOperationService,
        smtp_repository: SmtpAccountRepository,
        template_repository: MailTemplateRepository,
        fair_repository: FairRepository,
        customer_repository: CustomerRepository,
        authorization: AuthorizationPort,
        session: Session,
    ) -> None:
        self._repository = repository
        self._mail_send_operations = mail_send_operations
        self._smtp_repository = smtp_repository
        self._template_repository = template_repository
        self._fair_repository = fair_repository
        self._customer_repository = customer_repository
        self._authorization = authorization
        self._session = session

    def execute(self, command: RetryMailSendOperationCommand) -> RetryMailSendOperationResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        record = self._repository.get_by_id(command.organization_id, command.operation_id)
        if record is None:
            raise MailSendOperationNotFoundError("Mail send operation not found")

        if record.status != MailSendOperationStatus.FAILED:
            raise InvalidMailSendOperationTransitionError(
                "Only failed mail send operations can be retried",
            )

        if record.source_type == MailSendSourceType.FAIR_BULK_EMAIL:
            return self._retry_fair_bulk_email(command, record)

        if record.source_type not in RETRYABLE_SOURCE_TYPES:
            raise MailSendOperationRetryNotSupportedError(
                f"Retry is not supported for source type: {record.source_type}",
            )

        try:
            account = self._resolve_smtp_account(command.organization_id, record)
            if record.source_type == MailSendSourceType.TEMPLATE_TEST:
                self._validate_template(command.organization_id, record)
        except SmtpMailDeliveryError as exc:
            return self._complete_failed_retry(command, record, exc)

        body_text = record.body_text or record.subject

        def send_fn() -> None:
            send_smtp_message(
                account,
                recipient=record.recipient_email,
                subject=record.subject,
                body=body_text,
                body_html=record.body_html,
            )

        try:
            updated = self._mail_send_operations.execute_retry_synchronous(
                command.organization_id,
                record.id,
                send_fn=send_fn,
            )
        except SmtpMailDeliveryError:
            updated = self._repository.get_by_id(command.organization_id, record.id)
            if updated is None:
                raise MailSendOperationNotFoundError("Mail send operation not found") from None

        return self._build_result(command, updated)

    def _retry_fair_bulk_email(self, command: RetryMailSendOperationCommand, record) -> RetryMailSendOperationResult:
        handler = FairBulkEmailOperationRetryHandler(self._session)
        outbox = handler.get_outbox_for_operation(command.organization_id, record.id)
        if outbox is None:
            raise MailSendOperationRetryNotSupportedError(
                "Linked fair bulk email outbox record not found",
            )

        batch_id = record.batch_id or outbox.batch_id
        batch = handler.get_batch(command.organization_id, batch_id)
        if batch is None:
            raise MailSendOperationRetryNotSupportedError(
                "Linked fair bulk email batch not found",
            )

        try:
            handler.validate_consent(command.organization_id, outbox)
            account = self._resolve_smtp_account(command.organization_id, record)
            final_subject, body_text, body_html = handler.build_send_payload(
                command.organization_id,
                batch=batch,
                outbox=outbox,
            )
        except SmtpMailDeliveryError as exc:
            message = exc.args[0] if exc.args else "Mail gönderimi başarısız oldu."
            handler.sync_outbox_failed(outbox.id, message=message)
            self._session.flush()
            return self._complete_failed_retry(command, record, exc)

        handler.prepare_outbox_for_retry(outbox.id)
        self._session.flush()
        recipient = record.recipient_email or outbox.email

        def send_fn() -> None:
            handler.mark_outbox_sending(outbox.id)
            send_smtp_message(
                account,
                recipient=recipient,
                subject=final_subject,
                body=body_text,
                body_html=body_html,
            )

        try:
            updated = self._mail_send_operations.execute_retry_synchronous(
                command.organization_id,
                record.id,
                send_fn=send_fn,
            )
            self._repository.update_rendered_content(
                command.organization_id,
                record.id,
                subject=final_subject,
                body_html=body_html,
                body_text=body_text,
            )
            handler.sync_outbox_sent(
                outbox.id,
                subject=final_subject,
                body_html=body_html,
                body_text=body_text,
            )
        except SmtpMailDeliveryError:
            updated = self._repository.get_by_id(command.organization_id, record.id)
            if updated is None:
                raise MailSendOperationNotFoundError("Mail send operation not found") from None
            message = updated.error_message or "Mail gönderimi başarısız oldu."
            handler.sync_outbox_failed(outbox.id, message=message)

        self._session.flush()
        return self._build_result(command, updated)

    def _build_result(
        self,
        command: RetryMailSendOperationCommand,
        updated,
    ) -> RetryMailSendOperationResult:
        list_item = build_mail_send_operation_list_item(
            command.organization_id,
            updated,
            smtp_repository=self._smtp_repository,
            template_repository=self._template_repository,
            fair_repository=self._fair_repository,
            customer_repository=self._customer_repository,
        )
        return RetryMailSendOperationResult(
            success=updated.status == MailSendOperationStatus.SENT,
            operation=list_item,
        )

    def _complete_failed_retry(
        self,
        command: RetryMailSendOperationCommand,
        record,
        exc: SmtpMailDeliveryError,
    ) -> RetryMailSendOperationResult:
        message = exc.args[0] if exc.args else "Mail gönderimi başarısız oldu."
        self._mail_send_operations.append_operation_log(
            command.organization_id,
            record.id,
            event="retry_requested",
            message="Retry requested by admin",
        )
        self._repository.prepare_for_retry(command.organization_id, record.id)
        self._mail_send_operations.append_operation_log(
            command.organization_id,
            record.id,
            event="queued",
            message="Mail retry kuyruğa alındı",
        )
        self._mail_send_operations.mark_failed(
            command.organization_id,
            record.id,
            error_code=exc.error_type,
            error_message=message,
        )
        updated = self._repository.get_by_id(command.organization_id, record.id)
        if updated is None:
            raise MailSendOperationNotFoundError("Mail send operation not found")
        return self._build_result(command, updated)

    def _resolve_smtp_account(self, organization_id: UUID, record):
        if record.smtp_account_id is None:
            raise SmtpMailDeliveryError(
                "SMTP account is required for retry",
                error_type="MissingSmtpAccount",
            )
        account = self._smtp_repository.get_by_id(organization_id, record.smtp_account_id)
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

    def _validate_template(self, organization_id: UUID, record) -> None:
        if record.template_id is None:
            raise SmtpMailDeliveryError(
                "Mail template is required for retry",
                error_type="MissingTemplate",
            )
        template = self._template_repository.get_by_id(organization_id, record.template_id)
        if template is None or template.deleted_at is not None:
            raise SmtpMailDeliveryError(
                "Mail template not found",
                error_type="MailTemplateNotFound",
            )
        if not template.is_active:
            raise SmtpMailDeliveryError(
                "Mail template is inactive",
                error_type="InactiveTemplate",
            )

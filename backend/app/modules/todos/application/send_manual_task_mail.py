"""Queue per-recipient manual task mail operations (no SMTP send in-request)."""

from __future__ import annotations

from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.mail_send_operations.application.mail_send_operation_service import (
    MailSendOperationService,
)
from app.modules.mail_send_operations.domain.value_objects import MailSendSourceType
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
)
from app.modules.mail_templates.domain.exceptions import (
    MailTemplateAlreadyDeletedError,
    MailTemplateNotFoundError,
)
from app.modules.mail_templates.domain.ports import MailTemplateRepository
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)
from app.modules.smtp.domain.exceptions import SmtpAccountAlreadyDeletedError, SmtpAccountNotFoundError
from app.modules.smtp.domain.ports import SmtpAccountRepository
from app.modules.todos.application.worklist_commands import (
    SendManualTaskMailCommand,
    SendManualTaskMailResult,
)
from app.modules.todos.domain.exceptions import (
    InvalidManualTaskMailContentError,
    InvalidManualTaskMailRecipientsError,
    TodoMissingSourceFairError,
    TodoNotFoundError,
    WorklistCustomerNotInTodoError,
)
from app.modules.todos.domain.ports import TodoRepository
from app.shared.email import sanitize_scraped_email

PERMISSION_MAIL_SEND_EXECUTE = "fair_crm.mail_send_operations.execute"
QUEUED_MESSAGE = "Mail gönderimleri kuyruğa alındı."
INACTIVE_SMTP_MESSAGE = "Seçilen SMTP hesabı pasif durumda."


def parse_manual_task_mail_recipients(value: str) -> list[str]:
    """Parse semicolon/comma-separated recipients via shared sanitize+validate.

    Unsalvageable tokens raise; leading/trailing whitespace around tokens is trimmed.
    """
    text = (value or "").strip()
    if not text:
        raise InvalidManualTaskMailRecipientsError("En az bir alıcı e-posta adresi gerekli.")

    text = text.replace(",", ";")
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in text.split(";"):
        part = raw.strip()
        if not part:
            continue
        cleaned = sanitize_scraped_email(part)
        if cleaned is None:
            raise InvalidManualTaskMailRecipientsError(f"Geçersiz e-posta adresi: {part}")
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)

    if not normalized:
        raise InvalidManualTaskMailRecipientsError("En az bir alıcı e-posta adresi gerekli.")
    return normalized


def _looks_like_html(body: str) -> bool:
    return "<" in body and ">" in body


class SendManualTaskMailUseCase:
    def __init__(
        self,
        todo_repository: TodoRepository,
        participation_repository: SqlAlchemyParticipationRepository,
        smtp_repository: SmtpAccountRepository,
        template_repository: MailTemplateRepository,
        mail_send_operations: MailSendOperationService,
        authorization: AuthorizationPort,
        session=None,
    ) -> None:
        self._todo_repository = todo_repository
        self._participation_repository = participation_repository
        self._smtp_repository = smtp_repository
        self._template_repository = template_repository
        self._mail_send_operations = mail_send_operations
        self._authorization = authorization
        self._session = session

    def execute(self, command: SendManualTaskMailCommand) -> SendManualTaskMailResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_MAIL_SEND_EXECUTE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        subject = command.subject.strip()
        body = command.body.strip()
        if not subject:
            raise InvalidManualTaskMailContentError("Mail konusu boş olamaz.")
        if not body:
            raise InvalidManualTaskMailContentError("Mail gövdesi boş olamaz.")

        recipients = parse_manual_task_mail_recipients(command.recipients)

        todo = self._todo_repository.get_by_id(command.organization_id, command.todo_id)
        if todo is None:
            raise TodoNotFoundError("Todo not found")
        if todo.source_fair_id is None:
            raise TodoMissingSourceFairError("Todo source fair is required for worklist")

        participation = self._participation_repository.get_active_by_customer_and_fair(
            command.organization_id,
            command.customer_id,
            todo.source_fair_id,
        )
        if participation is None:
            raise WorklistCustomerNotInTodoError("Customer is not in this todo worklist")

        account = self._smtp_repository.get_by_id(command.organization_id, command.email_account_id)
        if account is None:
            raise SmtpAccountNotFoundError("SMTP account not found")
        if account.deleted_at is not None:
            raise SmtpAccountAlreadyDeletedError("SMTP account is deleted")
        if not account.is_active:
            raise SmtpAccountNotFoundError(INACTIVE_SMTP_MESSAGE)

        template_id = command.template_id
        if template_id is not None:
            template = self._template_repository.get_by_id(command.organization_id, template_id)
            if template is None:
                raise MailTemplateNotFoundError("Mail template not found")
            if template.deleted_at is not None:
                raise MailTemplateAlreadyDeletedError("Mail template is deleted")

        from app.shared.consent import EmailConsentBlockedError
        from app.shared.email_consent_policy import EmailConsentPolicy

        policy = EmailConsentPolicy(self._session) if self._session is not None else None
        allowed_recipients: list[str] = []
        blocked_messages: list[str] = []
        for recipient in recipients:
            if policy is None:
                allowed_recipients.append(recipient)
                continue
            decision = policy.evaluate(
                command.organization_id,
                email=recipient,
                customer_id=command.customer_id,
            )
            if decision.allowed:
                allowed_recipients.append(recipient)
            else:
                blocked_messages.append(decision.message or "E-posta iletişim izni kapalı")

        if not allowed_recipients:
            detail = blocked_messages[0] if blocked_messages else "E-posta iletişim izni kapalı"
            raise InvalidManualTaskMailRecipientsError(detail)

        body_html = body if _looks_like_html(body) else None
        operation_ids: list[UUID] = []
        for recipient in allowed_recipients:
            metadata = {
                "source": MailSendSourceType.MANUAL_TASK_MAIL.value,
                "todo_id": str(command.todo_id),
                "customer_id": str(command.customer_id),
                "recipient": recipient,
                "email_account_id": str(command.email_account_id),
            }
            if template_id is not None:
                metadata["template_id"] = str(template_id)

            try:
                operation = self._mail_send_operations.create_mail_send_operation(
                    CreateMailSendOperationParams(
                        organization_id=command.organization_id,
                        source_type=MailSendSourceType.MANUAL_TASK_MAIL,
                        recipient_email=recipient,
                        subject=subject,
                        body_text=body,
                        body_html=body_html,
                        email_account_id=command.email_account_id,
                        template_id=template_id,
                        customer_id=command.customer_id,
                        max_retry_count=account.max_delivery_attempts,
                        metadata_json=metadata,
                    )
                )
            except EmailConsentBlockedError as exc:
                raise InvalidManualTaskMailRecipientsError(
                    exc.decision.message or "E-posta iletişim izni kapalı"
                ) from exc
            operation_ids.append(operation.id)

        return SendManualTaskMailResult(
            queued_count=len(operation_ids),
            operation_ids=operation_ids,
            message=QUEUED_MESSAGE,
        )

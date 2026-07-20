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
from app.shared.email import is_valid_email_address

PERMISSION_CREATE = "fair_crm.todos.create"
QUEUED_MESSAGE = "Mail gönderimleri kuyruğa alındı."
INACTIVE_SMTP_MESSAGE = "Seçilen SMTP hesabı pasif durumda."


def parse_manual_task_mail_recipients(value: str) -> list[str]:
    """Parse semicolon/comma-separated recipients; reject invalid or empty input.

    Only leading/trailing whitespace around each token is stripped. Internal spaces
    are not removed — invalid tokens cause the whole parse to fail.
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
        # Validate the stripped token as-is (case preserved for the error message).
        # Do not delete internal whitespace to coerce validity.
        if not is_valid_email_address(part):
            raise InvalidManualTaskMailRecipientsError(f"Geçersiz e-posta adresi: {part}")
        email = part.lower()
        if email in seen:
            continue
        seen.add(email)
        normalized.append(email)

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
    ) -> None:
        self._todo_repository = todo_repository
        self._participation_repository = participation_repository
        self._smtp_repository = smtp_repository
        self._template_repository = template_repository
        self._mail_send_operations = mail_send_operations
        self._authorization = authorization

    def execute(self, command: SendManualTaskMailCommand) -> SendManualTaskMailResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
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

        account = self._smtp_repository.get_by_id(command.organization_id, command.smtp_account_id)
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

        body_html = body if _looks_like_html(body) else None
        operation_ids: list[UUID] = []
        for recipient in recipients:
            metadata = {
                "source": MailSendSourceType.MANUAL_TASK_MAIL.value,
                "todo_id": str(command.todo_id),
                "customer_id": str(command.customer_id),
                "recipient": recipient,
                "smtp_account_id": str(command.smtp_account_id),
            }
            if template_id is not None:
                metadata["template_id"] = str(template_id)

            operation = self._mail_send_operations.create_mail_send_operation(
                CreateMailSendOperationParams(
                    organization_id=command.organization_id,
                    source_type=MailSendSourceType.MANUAL_TASK_MAIL,
                    recipient_email=recipient,
                    subject=subject,
                    body_text=body,
                    body_html=body_html,
                    smtp_account_id=command.smtp_account_id,
                    template_id=template_id,
                    customer_id=command.customer_id,
                    metadata_json=metadata,
                )
            )
            operation_ids.append(operation.id)

        return SendManualTaskMailResult(
            queued_count=len(operation_ids),
            operation_ids=operation_ids,
            message=QUEUED_MESSAGE,
        )

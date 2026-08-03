from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.fairs.domain.ports import FairRepository
from app.modules.mail_send_operations.application.commands import RetryMailSendOperationCommand
from app.modules.mail_send_operations.application.list_mail_send_operations import (
    MailSendOperationListItem,
    build_mail_send_operation_list_item,
)
from app.modules.mail_send_operations.application.mail_send_operation_service import (
    MailSendOperationService,
)
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
from app.modules.smtp.domain.ports import SmtpAccountRepository

PERMISSION_UPDATE = "fair_crm.email_accounts.update"

RETRYABLE_SOURCE_TYPES = frozenset(
    {
        MailSendSourceType.FAIR_BULK_EMAIL,
        MailSendSourceType.SMTP_TEST,
        MailSendSourceType.TEMPLATE_TEST,
        MailSendSourceType.MANUAL_TASK_MAIL,
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
        if record.source_type not in RETRYABLE_SOURCE_TYPES:
            raise MailSendOperationRetryNotSupportedError(
                f"Retry is not supported for source type: {record.source_type}",
            )

        self._mail_send_operations.append_operation_log(
            command.organization_id,
            record.id,
            event="retry_requested",
            message="Retry requested by admin",
        )
        updated = self._repository.prepare_for_retry(command.organization_id, record.id)
        self._mail_send_operations.append_operation_log(
            command.organization_id,
            record.id,
            event="queued",
            message="Mail retry kuyruğa alındı",
        )
        updated = self._repository.get_by_id(command.organization_id, record.id) or updated
        list_item = build_mail_send_operation_list_item(
            command.organization_id,
            updated,
            smtp_repository=self._smtp_repository,
            template_repository=self._template_repository,
            fair_repository=self._fair_repository,
            customer_repository=self._customer_repository,
        )
        return RetryMailSendOperationResult(success=True, operation=list_item)

import re

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.mail_send_operations.application.mail_send_operation_service import MailSendOperationService
from app.modules.mail_send_operations.domain.value_objects import MailSendSourceType
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
)
from app.modules.smtp.application.commands import SendTestSmtpMailCommand, SendTestSmtpMailResult
from app.modules.smtp.application.smtp_test_debug import (
    build_test_mail_failure_result,
    log_smtp_test_mail_failure,
)
from app.modules.smtp.domain.exceptions import (
    InvalidSmtpTestRecipientError,
    SmtpAccountAlreadyDeletedError,
    SmtpAccountNotFoundError,
    SmtpMailDeliveryError,
)
from app.modules.smtp.domain.ports import SmtpAccountRepository
from app.modules.smtp.domain.smtp_config_validation import smtp_config_warnings
from app.modules.smtp.infrastructure.smtp_mailer import send_smtp_message

PERMISSION_UPDATE = "fair_crm.smtp.update"
_RECIPIENT_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class SendTestSmtpMailUseCase:
    def __init__(
        self,
        repository: SmtpAccountRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
        mail_send_operations: MailSendOperationService,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit
        self._mail_send_operations = mail_send_operations

    def execute(self, command: SendTestSmtpMailCommand) -> SendTestSmtpMailResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        recipient = command.recipient.strip()
        if not recipient or not _RECIPIENT_PATTERN.match(recipient):
            raise InvalidSmtpTestRecipientError("Valid recipient email is required")

        account = self._repository.get_by_id(command.organization_id, command.account_id)
        if account is None:
            raise SmtpAccountNotFoundError("SMTP account not found")
        if account.deleted_at is not None:
            raise SmtpAccountAlreadyDeletedError("SMTP account is deleted")

        subject = "FAIR CRM SMTP Test"
        body = (
            "This is a test message from FAIR CRM SMTP settings.\n"
            "If you received this email, the SMTP configuration is working."
        )

        if not account.is_active:
            log_smtp_test_mail_failure(
                account=account,
                organization_id=command.organization_id,
                recipient=recipient,
                reason="inactive_account",
            )
            inactive_exc = SmtpMailDeliveryError(
                "SMTP account is inactive",
                error_type="InactiveAccount",
                raw_message="SMTP account is inactive",
            )
            self._mail_send_operations.record_immediate_failure(
                CreateMailSendOperationParams(
                    organization_id=command.organization_id,
                    source_type=MailSendSourceType.SMTP_TEST,
                    recipient_email=recipient,
                    subject=subject,
                    body_text=body,
                    smtp_account_id=account.id,
                    metadata_json={"smtp_account_name": account.name},
                ),
                error_code="InactiveAccount",
                error_message="SMTP account is inactive",
            )
            return build_test_mail_failure_result(account, recipient=recipient, exc=inactive_exc)

        operation_params = CreateMailSendOperationParams(
            organization_id=command.organization_id,
            source_type=MailSendSourceType.SMTP_TEST,
            recipient_email=recipient,
            subject=subject,
            body_text=body,
            smtp_account_id=account.id,
            metadata_json={"smtp_account_name": account.name},
        )

        try:
            self._mail_send_operations.execute_synchronous_send(
                operation_params,
                send_fn=lambda: send_smtp_message(
                    account,
                    recipient=recipient,
                    subject=subject,
                    body=body,
                ),
            )
        except SmtpMailDeliveryError as exc:
            log_smtp_test_mail_failure(
                account=account,
                organization_id=command.organization_id,
                recipient=recipient,
                exc=exc,
            )
            return build_test_mail_failure_result(account, recipient=recipient, exc=exc)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.smtp_account.test_mail_sent",
            resource_type="smtp_account",
            resource_id=str(account.id),
            new_values={"recipient": recipient},
            metadata={"user_id": str(command.user_id)},
        )

        return SendTestSmtpMailResult(
            success=True,
            message="Test email sent successfully",
            smtp_host=account.host,
            smtp_port=account.port,
            encryption_type=account.encryption_type,
            config_warnings=tuple(smtp_config_warnings(account.port, account.encryption_type)),
        )

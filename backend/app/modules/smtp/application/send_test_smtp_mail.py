import re

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.smtp.application.commands import SendTestSmtpMailCommand, SendTestSmtpMailResult
from app.modules.smtp.domain.exceptions import (
    InvalidSmtpTestRecipientError,
    SmtpAccountAlreadyDeletedError,
    SmtpAccountNotFoundError,
    SmtpMailDeliveryError,
)
from app.modules.smtp.domain.ports import SmtpAccountRepository
from app.modules.smtp.infrastructure.smtp_mailer import send_smtp_message

PERMISSION_UPDATE = "fair_crm.smtp.update"
_RECIPIENT_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class SendTestSmtpMailUseCase:
    def __init__(
        self,
        repository: SmtpAccountRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

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
        if not account.is_active:
            raise SmtpMailDeliveryError("SMTP account is inactive")

        send_smtp_message(
            account,
            recipient=recipient,
            subject="FAIR CRM SMTP Test",
            body=(
                "This is a test message from FAIR CRM SMTP settings.\n"
                "If you received this email, the SMTP configuration is working."
            ),
        )

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
        )

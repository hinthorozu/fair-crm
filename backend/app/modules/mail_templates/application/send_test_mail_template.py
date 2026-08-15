from dataclasses import dataclass
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.email_delivery.application.email_delivery_service import EmailDeliveryService
from app.modules.mail_templates.application.commands import SendTestMailTemplateCommand
from app.modules.mail_templates.domain.exceptions import (
    MailTemplateAlreadyDeletedError,
    MailTemplateDefaultSmtpNotFoundError,
    MailTemplateInactiveForTestError,
    MailTemplateNotFoundError,
)
from app.modules.mail_templates.domain.ports import MailTemplateRepository, MailTemplateRenderer
from app.modules.smtp.domain.exceptions import SmtpAccountAlreadyDeletedError, SmtpAccountNotFoundError
from app.modules.smtp.domain.ports import SmtpAccountRepository

PERMISSION_EXECUTE = "fair_crm.mail_templates.execute"
DEFAULT_SMTP_MESSAGE = "Bu kuruluş için varsayılan e-posta hesabı bulunamadı."
INACTIVE_SMTP_MESSAGE = "Seçilen e-posta hesabı pasif durumda."
INACTIVE_TEMPLATE_MESSAGE = "Pasif mail şablonu ile test e-postası gönderilemez."


@dataclass(frozen=True)
class SendTestMailTemplateResult:
    success: bool
    message: str


class SendTestMailTemplateUseCase:
    def __init__(
        self,
        repository: MailTemplateRepository,
        renderer: MailTemplateRenderer,
        smtp_repository: SmtpAccountRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._repository = repository
        self._renderer = renderer
        self._smtp_repository = smtp_repository
        self._authorization = authorization

    def execute(self, command: SendTestMailTemplateCommand) -> SendTestMailTemplateResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_EXECUTE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        template = self._repository.get_by_id(command.organization_id, command.template_id)
        if template is None:
            raise MailTemplateNotFoundError("Mail template not found")
        if template.deleted_at is not None:
            raise MailTemplateAlreadyDeletedError("Mail template is deleted")
        if not template.is_active:
            raise MailTemplateInactiveForTestError(INACTIVE_TEMPLATE_MESSAGE)

        account = self._resolve_smtp_account(command.organization_id, command.email_account_id)
        if account is None:
            if command.email_account_id is not None:
                raise SmtpAccountNotFoundError("SMTP account not found")
            raise MailTemplateDefaultSmtpNotFoundError(DEFAULT_SMTP_MESSAGE)
        if account.deleted_at is not None:
            raise SmtpAccountAlreadyDeletedError("SMTP account is deleted")
        if not account.is_active:
            raise SmtpAccountNotFoundError(INACTIVE_SMTP_MESSAGE)

        rendered = self._renderer.render(template, command.variables)
        subject = command.subject_override.strip() if command.subject_override else rendered.subject
        EmailDeliveryService.send(
            account,
            to=command.to_email,
            subject=subject,
            body_html=rendered.body_html,
            body_text=rendered.body_text,
        )
        return SendTestMailTemplateResult(
            success=True,
            message="Test e-postası gönderildi.",
        )

    def _resolve_smtp_account(self, organization_id: UUID, account_id: UUID | None):
        if account_id is not None:
            return self._smtp_repository.get_by_id(organization_id, account_id)
        return self._smtp_repository.get_default_for_organization(organization_id)

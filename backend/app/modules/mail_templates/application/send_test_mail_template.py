import re

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.mail_send_operations.application.mail_send_operation_service import MailSendOperationService
from app.modules.mail_send_operations.domain.value_objects import MailSendSourceType
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
)
from app.modules.mail_templates.application.commands import SendTestMailTemplateCommand, SendTestMailTemplateResult
from app.modules.mail_templates.application.mail_template_test_debug import (
    SMTP_PASSWORD_USER_MESSAGE,
    log_mail_template_test_email_failure,
)
from app.modules.mail_templates.domain.exceptions import (
    InvalidMailTemplateTestRecipientError,
    InvalidMailTemplateTestSubjectError,
    MailTemplateAlreadyDeletedError,
    MailTemplateDefaultSmtpNotFoundError,
    MailTemplateInactiveForTestError,
    MailTemplateNotFoundError,
    MailTemplateRenderError,
)
from app.modules.mail_templates.domain.ports import MailTemplateRepository, MailTemplateRenderer
from app.modules.smtp.domain.exceptions import (
    SmtpAccountAlreadyDeletedError,
    SmtpAccountNotFoundError,
    SmtpMailDeliveryError,
)
from app.modules.smtp.domain.ports import SmtpAccountRepository
from app.modules.smtp.infrastructure.smtp_mailer import send_smtp_message

PERMISSION_TEST_SEND = "fair_crm.mail_templates.test_send"
_RECIPIENT_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
RENDER_USER_MESSAGE = "Mail şablonu render edilirken hata oluştu. Değişkenleri kontrol edin."
DEFAULT_SMTP_USER_MESSAGE = "Bu kuruluş için varsayılan SMTP hesabı bulunamadı."
INACTIVE_TEMPLATE_USER_MESSAGE = "Pasif mail şablonu ile test email gönderilemez."
INACTIVE_SMTP_USER_MESSAGE = "Seçilen SMTP hesabı pasif durumda."


class SendTestMailTemplateUseCase:
    def __init__(
        self,
        template_repository: MailTemplateRepository,
        smtp_repository: SmtpAccountRepository,
        renderer: MailTemplateRenderer,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
        mail_send_operations: MailSendOperationService,
    ) -> None:
        self._template_repository = template_repository
        self._smtp_repository = smtp_repository
        self._renderer = renderer
        self._authorization = authorization
        self._audit = audit
        self._mail_send_operations = mail_send_operations

    def execute(self, command: SendTestMailTemplateCommand) -> SendTestMailTemplateResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_TEST_SEND,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        recipient = command.to_email.strip()
        if not recipient or not _RECIPIENT_PATTERN.match(recipient):
            raise InvalidMailTemplateTestRecipientError("Geçerli bir test alıcı e-posta adresi girin.")

        template = self._template_repository.get_by_id(command.organization_id, command.template_id)
        if template is None:
            raise MailTemplateNotFoundError("Mail template not found")
        if template.deleted_at is not None:
            raise MailTemplateAlreadyDeletedError("Mail template is deleted")
        if not template.is_active:
            raise MailTemplateInactiveForTestError(INACTIVE_TEMPLATE_USER_MESSAGE)

        try:
            rendered_subject = self._renderer.render(template.subject, command.variables)
            rendered_body_html = (
                self._renderer.render(template.body_html, command.variables)
                if template.body_html
                else None
            )
            rendered_body_text = (
                self._renderer.render(template.body_text, command.variables)
                if template.body_text
                else None
            )
        except MailTemplateRenderError as exc:
            raise MailTemplateRenderError(RENDER_USER_MESSAGE) from exc

        final_subject = rendered_subject
        if command.subject_override is not None:
            overridden = command.subject_override.strip()
            if not overridden:
                raise InvalidMailTemplateTestSubjectError("Test mail konusu boş olamaz.")
            final_subject = overridden

        account = self._resolve_smtp_account(command)
        if account is None:
            if command.smtp_account_id is not None:
                raise SmtpAccountNotFoundError("SMTP account not found")
            raise MailTemplateDefaultSmtpNotFoundError(DEFAULT_SMTP_USER_MESSAGE)
        if account.deleted_at is not None:
            raise SmtpAccountAlreadyDeletedError("SMTP account is deleted")

        body_text = rendered_body_text or final_subject
        if not account.is_active:
            log_mail_template_test_email_failure(
                template=template,
                organization_id=command.organization_id,
                smtp_account=account,
                to_email=recipient,
                reason="inactive_smtp_account",
            )
            self._mail_send_operations.record_immediate_failure(
                CreateMailSendOperationParams(
                    organization_id=command.organization_id,
                    source_type=MailSendSourceType.TEMPLATE_TEST,
                    recipient_email=recipient,
                    subject=final_subject,
                    body_text=body_text,
                    body_html=rendered_body_html,
                    smtp_account_id=account.id,
                    template_id=template.id,
                    metadata_json={"template_key": template.key},
                ),
                error_code="InactiveAccount",
                error_message=INACTIVE_SMTP_USER_MESSAGE,
            )
            return SendTestMailTemplateResult(
                success=False,
                message=INACTIVE_SMTP_USER_MESSAGE,
                smtp_host=account.host,
                smtp_port=account.port,
                template_key=template.key,
            )

        operation_params = CreateMailSendOperationParams(
            organization_id=command.organization_id,
            source_type=MailSendSourceType.TEMPLATE_TEST,
            recipient_email=recipient,
            subject=final_subject,
            body_text=body_text,
            body_html=rendered_body_html,
            smtp_account_id=account.id,
            template_id=template.id,
            metadata_json={"template_key": template.key},
        )

        try:
            self._mail_send_operations.execute_synchronous_send(
                operation_params,
                send_fn=lambda: send_smtp_message(
                    account,
                    recipient=recipient,
                    subject=final_subject,
                    body=body_text,
                    body_html=rendered_body_html,
                ),
            )
        except SmtpMailDeliveryError as exc:
            log_mail_template_test_email_failure(
                template=template,
                organization_id=command.organization_id,
                smtp_account=account,
                to_email=recipient,
                exc=exc,
            )
            message = exc.args[0] if exc.args else "SMTP gönderimi başarısız oldu."
            if exc.error_type == "MissingPassword":
                message = SMTP_PASSWORD_USER_MESSAGE
            return SendTestMailTemplateResult(
                success=False,
                message=message,
                smtp_host=account.host,
                smtp_port=account.port,
                template_key=template.key,
            )

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.mail_template.test_email_sent",
            resource_type="mail_template",
            resource_id=str(template.id),
            new_values={
                "to_email": recipient,
                "smtp_account_id": str(account.id),
                "template_key": template.key,
            },
            metadata={"user_id": str(command.user_id)},
        )

        return SendTestMailTemplateResult(
            success=True,
            message="Test mail başarıyla gönderildi.",
            smtp_host=account.host,
            smtp_port=account.port,
            template_key=template.key,
        )

    def _resolve_smtp_account(self, command: SendTestMailTemplateCommand):
        if command.smtp_account_id is not None:
            return self._smtp_repository.get_by_id(command.organization_id, command.smtp_account_id)
        return self._smtp_repository.get_default_for_organization(command.organization_id)

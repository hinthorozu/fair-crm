from dataclasses import dataclass
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fair_emails.application.commands import SendBulkEmailCommand
from app.modules.fair_emails.application.fair_bulk_mail_operation_sync import FairBulkEmailMailOperationSync
from app.modules.fair_emails.application.recipient_service import FairBulkEmailRecipientService
from app.modules.fair_emails.domain.exceptions import (
    FairBulkEmailRecipientNotFoundError,
    FairNotEligibleForBulkEmailError,
)
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    FairEmailBatchRecord,
    SqlAlchemyFairEmailBatchRepository,
)
from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository
from app.modules.mail_templates.domain.exceptions import (
    MailTemplateAlreadyDeletedError,
    MailTemplateDefaultSmtpNotFoundError,
    MailTemplateInactiveForTestError,
    MailTemplateNotFoundError,
)
from app.modules.mail_templates.domain.ports import MailTemplateRepository
from app.modules.smtp.domain.exceptions import SmtpAccountAlreadyDeletedError, SmtpAccountNotFoundError
from app.modules.smtp.domain.ports import SmtpAccountRepository

PERMISSION_SEND = "fair_crm.fair_emails.send"
INACTIVE_TEMPLATE_MESSAGE = "Pasif mail şablonu ile toplu mail gönderilemez."
DEFAULT_SMTP_MESSAGE = "Bu kuruluş için varsayılan SMTP hesabı bulunamadı."
INACTIVE_SMTP_MESSAGE = "Seçilen SMTP hesabı pasif durumda."


@dataclass(frozen=True)
class SendBulkEmailResult:
    batch_id: UUID
    status: str
    total_count: int
    skipped_count: int
    message: str


class SendFairBulkEmailUseCase:
    def __init__(
        self,
        fair_repository: FairRepository,
        template_repository: MailTemplateRepository,
        smtp_repository: SmtpAccountRepository,
        batch_repository: SqlAlchemyFairEmailBatchRepository,
        recipient_service: FairBulkEmailRecipientService,
        mail_operation_sync: FairBulkEmailMailOperationSync,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._fair_repository = fair_repository
        self._template_repository = template_repository
        self._smtp_repository = smtp_repository
        self._batch_repository = batch_repository
        self._recipient_service = recipient_service
        self._mail_operation_sync = mail_operation_sync
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: SendBulkEmailCommand) -> SendBulkEmailResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_SEND,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        fair = self._fair_repository.get_by_id(command.organization_id, command.fair_id)
        if fair is None:
            raise FairNotFoundError("Fair not found")
        if fair.deleted_at is not None:
            raise FairNotEligibleForBulkEmailError("Arşivlenmiş fuar için toplu mail gönderilemez.")

        template = self._template_repository.get_by_id(command.organization_id, command.template_id)
        if template is None:
            raise MailTemplateNotFoundError("Mail template not found")
        if template.deleted_at is not None:
            raise MailTemplateAlreadyDeletedError("Mail template is deleted")
        if not template.is_active:
            raise MailTemplateInactiveForTestError(INACTIVE_TEMPLATE_MESSAGE)

        account = self._resolve_smtp_account(command)
        if account is None:
            if command.smtp_account_id is not None:
                raise SmtpAccountNotFoundError("SMTP account not found")
            raise MailTemplateDefaultSmtpNotFoundError(DEFAULT_SMTP_MESSAGE)
        if account.deleted_at is not None:
            raise SmtpAccountAlreadyDeletedError("SMTP account is deleted")
        if not account.is_active:
            raise SmtpAccountNotFoundError(INACTIVE_SMTP_MESSAGE)

        if command.subject_override is not None and not command.subject_override.strip():
            raise ValueError("Toplu mail konusu boş olamaz.")

        preview = self._recipient_service.preview(
            command.organization_id,
            command.fair_id,
            command.recipient_options,
        )
        will_send = [item for item in preview.recipients if item.status == "will_send"]
        if not will_send:
            raise FairBulkEmailRecipientNotFoundError("Gönderilecek alıcı bulunamadı.")

        batch = self._batch_repository.create_batch(
            organization_id=command.organization_id,
            fair_id=command.fair_id,
            template_id=command.template_id,
            smtp_account_id=account.id,
            subject_override=command.subject_override.strip() if command.subject_override else None,
            recipient_options=command.recipient_options,
            created_by_user_id=command.user_id,
            recipients=preview.recipients,
        )

        default_subject = command.subject_override.strip() if command.subject_override else template.subject
        self._mail_operation_sync.ensure_operations_for_batch(
            organization_id=command.organization_id,
            batch=batch,
            default_subject=default_subject,
        )
        self._mail_operation_sync.create_skipped_operations_for_consent(
            organization_id=command.organization_id,
            batch=batch,
            default_subject=default_subject,
            recipients=preview.recipients,
        )

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.fair_email.batch_queued",
            resource_type="fair_email_batch",
            resource_id=str(batch.id),
            new_values={
                "fair_id": str(command.fair_id),
                "template_id": str(command.template_id),
                "total_count": batch.total_count,
            },
            metadata={"user_id": str(command.user_id)},
        )

        return SendBulkEmailResult(
            batch_id=batch.id,
            status=batch.status,
            total_count=batch.total_count,
            skipped_count=batch.skipped_count,
            message="Toplu mail gönderimi kuyruğa alındı.",
        )

    def _resolve_smtp_account(self, command: SendBulkEmailCommand):
        if command.smtp_account_id is not None:
            return self._smtp_repository.get_by_id(command.organization_id, command.smtp_account_id)
        return self._smtp_repository.get_default_for_organization(command.organization_id)

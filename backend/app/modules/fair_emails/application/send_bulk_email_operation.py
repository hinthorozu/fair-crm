"""Create a fair_emails batch for Operations bulk_email (manual or multi-fair)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort, AuditPort
from app.modules.fair_emails.application.excel_email_extract import extract_email_tokens_from_xlsx
from app.modules.fair_emails.application.fair_bulk_mail_operation_sync import FairBulkEmailMailOperationSync
from app.modules.fair_emails.application.recipient_resolution import (
    resolve_manual_and_excel_emails,
    resolved_to_wizard_recipient,
    wizard_to_resolved_recipient,
)
from app.modules.fair_emails.application.recipient_service import FairBulkEmailRecipientService
from app.modules.fair_emails.domain.exceptions import (
    FairBulkEmailRecipientNotFoundError,
    FairNotEligibleForBulkEmailError,
)
from app.modules.fair_emails.domain.value_objects import RecipientOptions, ResolvedRecipient
from app.modules.fair_emails.infrastructure.recipient_loader import ParticipationFilters
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    SqlAlchemyFairEmailBatchRepository,
)
from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository
from app.modules.imports.domain.exceptions import InvalidImportFileError
from app.modules.mail_templates.domain.exceptions import (
    MailTemplateAlreadyDeletedError,
    MailTemplateInactiveForTestError,
    MailTemplateNotFoundError,
)
from app.modules.mail_templates.domain.ports import MailTemplateRepository
from app.modules.smtp.domain.exceptions import SmtpAccountAlreadyDeletedError, SmtpAccountNotFoundError
from app.modules.smtp.domain.ports import SmtpAccountRepository

PERMISSION_SEND = "fair_crm.fair_emails.send"
INACTIVE_TEMPLATE_MESSAGE = "Pasif mail şablonu ile toplu mail gönderilemez."
INACTIVE_SMTP_MESSAGE = "Seçilen SMTP hesabı pasif durumda."


@dataclass(frozen=True)
class SendBulkEmailOperationCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    source_type: str
    template_id: UUID
    smtp_account_id: UUID
    subject: str
    fair_ids: list[UUID] | None = None
    manual_emails: str | None = None
    excel_email_tokens: list[str] | None = None
    excel_bytes: bytes | None = None
    country_filter: str | None = None
    city_filter: str | None = None
    company_name_contains: str | None = None
    recipient_options: RecipientOptions = RecipientOptions()
    operation_id: UUID | None = None


@dataclass(frozen=True)
class SendBulkEmailOperationResult:
    batch_id: UUID
    status: str
    total_count: int
    skipped_count: int
    will_send_count: int
    message: str


class SendBulkEmailOperationUseCase:
    """Operations wizard send — reuses fair_emails batch/outbox (nullable fair/CRM ids)."""

    def __init__(
        self,
        fair_repository: FairRepository,
        template_repository: MailTemplateRepository,
        smtp_repository: SmtpAccountRepository,
        batch_repository: SqlAlchemyFairEmailBatchRepository,
        recipient_service: FairBulkEmailRecipientService,
        mail_operation_sync: FairBulkEmailMailOperationSync,
        authorization: AuthorizationPort,
        audit: AuditPort | None = None,
    ) -> None:
        self._fair_repository = fair_repository
        self._template_repository = template_repository
        self._smtp_repository = smtp_repository
        self._batch_repository = batch_repository
        self._recipient_service = recipient_service
        self._mail_operation_sync = mail_operation_sync
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: SendBulkEmailOperationCommand) -> SendBulkEmailOperationResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_SEND,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        source_type = (command.source_type or "").strip().lower()
        if source_type not in {"manual", "fair_list"}:
            raise ValueError("Geçersiz alıcı kaynağı")

        subject = (command.subject or "").strip()
        if not subject:
            raise ValueError("Toplu mail konusu boş olamaz.")

        template = self._template_repository.get_by_id(command.organization_id, command.template_id)
        if template is None:
            raise MailTemplateNotFoundError("Mail template not found")
        if template.deleted_at is not None:
            raise MailTemplateAlreadyDeletedError("Mail template is deleted")
        if not template.is_active:
            raise MailTemplateInactiveForTestError(INACTIVE_TEMPLATE_MESSAGE)

        smtp = self._smtp_repository.get_by_id(command.organization_id, command.smtp_account_id)
        if smtp is None:
            raise SmtpAccountNotFoundError("SMTP account not found")
        if smtp.deleted_at is not None:
            raise SmtpAccountAlreadyDeletedError("SMTP account is deleted")
        if not smtp.is_active:
            raise SmtpAccountNotFoundError(INACTIVE_SMTP_MESSAGE)

        if source_type == "manual":
            recipients, fair_id, fair_ids = self._resolve_manual(command)
        else:
            recipients, fair_id, fair_ids = self._resolve_fair_list(command)

        will_send = [item for item in recipients if item.status == "will_send"]
        if not will_send:
            raise FairBulkEmailRecipientNotFoundError("Gönderilecek alıcı bulunamadı.")

        batch = self._batch_repository.create_batch(
            organization_id=command.organization_id,
            fair_id=fair_id,
            template_id=command.template_id,
            smtp_account_id=smtp.id,
            subject_override=subject,
            recipient_options=command.recipient_options,
            created_by_user_id=command.user_id,
            recipients=recipients,
            operation_id=command.operation_id,
            recipient_options_extra={
                "source_type": source_type,
                "fair_ids": [str(item) for item in fair_ids],
            },
        )

        self._mail_operation_sync.ensure_operations_for_batch(
            organization_id=command.organization_id,
            batch=batch,
            default_subject=subject,
        )
        if source_type == "fair_list":
            self._mail_operation_sync.create_skipped_operations_for_consent(
                organization_id=command.organization_id,
                batch=batch,
                default_subject=subject,
                recipients=recipients,
            )

        if self._audit is not None:
            self._audit.record_event(
                organization_id=command.organization_id,
                access_token=command.access_token,
                action="fair_crm.fair_email.operation_batch_queued",
                resource_type="fair_email_batch",
                resource_id=str(batch.id),
                new_values={
                    "source_type": source_type,
                    "template_id": str(command.template_id),
                    "total_count": batch.total_count,
                    "operation_id": str(command.operation_id) if command.operation_id else None,
                },
                metadata={"user_id": str(command.user_id)},
            )

        return SendBulkEmailOperationResult(
            batch_id=batch.id,
            status=batch.status,
            total_count=batch.total_count,
            skipped_count=batch.skipped_count,
            will_send_count=len(will_send),
            message="Toplu mail gönderimi kuyruğa alındı.",
        )

    def _resolve_manual(
        self, command: SendBulkEmailOperationCommand
    ) -> tuple[list[ResolvedRecipient], UUID | None, list[UUID]]:
        excel_tokens = list(command.excel_email_tokens or [])
        if command.excel_bytes:
            try:
                excel_tokens.extend(extract_email_tokens_from_xlsx(command.excel_bytes))
            except InvalidImportFileError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise InvalidImportFileError("Excel dosyası okunamadı") from exc

        manual_text = (command.manual_emails or "").strip()
        if not manual_text and not excel_tokens:
            raise ValueError("Excel dosyası yükleyin veya en az bir e-posta girin.")

        preview = resolve_manual_and_excel_emails(
            manual_emails_text=manual_text,
            excel_email_tokens=excel_tokens,
        )
        recipients = [wizard_to_resolved_recipient(item) for item in preview.recipients]
        return recipients, None, []

    def _resolve_fair_list(
        self, command: SendBulkEmailOperationCommand
    ) -> tuple[list[ResolvedRecipient], UUID | None, list[UUID]]:
        fair_ids = list(command.fair_ids or [])
        if not fair_ids:
            raise ValueError("En az bir fuar seçin.")

        for fair_id in fair_ids:
            fair = self._fair_repository.get_by_id(command.organization_id, fair_id)
            if fair is None:
                raise FairNotFoundError("Fair not found")
            if fair.deleted_at is not None:
                raise FairNotEligibleForBulkEmailError(
                    "Arşivlenmiş fuar için toplu mail gönderilemez."
                )

        preview = self._recipient_service.preview_for_fairs(
            command.organization_id,
            fair_ids,
            command.recipient_options,
            filters=ParticipationFilters(
                country=command.country_filter,
                city=command.city_filter,
                company_name_contains=command.company_name_contains,
            ),
        )
        # Keep ResolvedRecipient (CRM ids present); wizard round-trip preserves nullability.
        recipients = [
            wizard_to_resolved_recipient(resolved_to_wizard_recipient(item))
            for item in preview.recipients
        ]
        return recipients, fair_ids[0], fair_ids

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fair_emails.application.excel_email_extract import extract_email_tokens_from_xlsx
from app.modules.fair_emails.application.recipient_resolution import (
    build_render_variables,
    resolve_manual_and_excel_emails,
    resolved_to_wizard_recipient,
)
from app.modules.fair_emails.application.recipient_service import FairBulkEmailRecipientService
from app.modules.fair_emails.domain.exceptions import FairNotEligibleForBulkEmailError
from app.modules.fair_emails.domain.value_objects import (
    RecipientOptions,
    WizardPreviewRecipient,
)
from app.modules.fair_emails.infrastructure.recipient_loader import (
    FairBulkEmailRecipientLoader,
    ParticipationFilters,
)
from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository
from app.modules.imports.domain.exceptions import InvalidImportFileError
from app.modules.mail_templates.domain.exceptions import (
    MailTemplateAlreadyDeletedError,
    MailTemplateInactiveForTestError,
    MailTemplateNotFoundError,
    MailTemplateRenderError,
)
from app.modules.mail_templates.domain.ports import MailTemplateRepository, MailTemplateRenderer
from app.modules.smtp.domain.exceptions import SmtpAccountAlreadyDeletedError, SmtpAccountNotFoundError
from app.modules.smtp.domain.ports import SmtpAccountRepository

PERMISSION_PREVIEW = "fair_crm.fair_emails.preview"
INACTIVE_TEMPLATE_MESSAGE = "Pasif mail şablonu ile toplu mail gönderilemez."


@dataclass(frozen=True)
class PreviewBulkEmailOperationCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    source_type: str
    template_id: UUID
    smtp_account_id: UUID
    subject_override: str | None = None
    manual_emails: str | None = None
    excel_bytes: bytes | None = None
    fair_ids: list[UUID] | None = None
    country_filter: str | None = None
    city_filter: str | None = None
    company_name_contains: str | None = None
    recipient_options: RecipientOptions = RecipientOptions()


@dataclass(frozen=True)
class BulkEmailOperationMailPreview:
    template_id: UUID
    template_name: str
    smtp_account_id: UUID
    smtp_account_name: str
    rendered_subject: str
    body_html: str | None
    body_text: str | None


@dataclass(frozen=True)
class BulkEmailOperationRecipientSummary:
    source_type: str
    total_found: int | None
    valid_email_count: int
    duplicate_count: int | None
    invalid_count: int | None
    deduped_recipient_count: int
    skipped_count: int
    selected_fair_count: int | None
    selected_fair_names: list[str] | None
    total_customers: int | None
    total_contacts: int | None
    recipients: list[WizardPreviewRecipient]


@dataclass(frozen=True)
class BulkEmailOperationPreviewResult:
    recipients: BulkEmailOperationRecipientSummary
    mail: BulkEmailOperationMailPreview


class PreviewBulkEmailOperationUseCase:
    def __init__(
        self,
        fair_repository: FairRepository,
        template_repository: MailTemplateRepository,
        smtp_repository: SmtpAccountRepository,
        renderer: MailTemplateRenderer,
        recipient_service: FairBulkEmailRecipientService,
        recipient_loader: FairBulkEmailRecipientLoader,
        authorization: AuthorizationPort,
    ) -> None:
        self._fair_repository = fair_repository
        self._template_repository = template_repository
        self._smtp_repository = smtp_repository
        self._renderer = renderer
        self._recipient_service = recipient_service
        self._recipient_loader = recipient_loader
        self._authorization = authorization

    def execute(self, command: PreviewBulkEmailOperationCommand) -> BulkEmailOperationPreviewResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_PREVIEW,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        source_type = (command.source_type or "").strip().lower()
        if source_type not in {"manual", "fair_list"}:
            raise ValueError("Geçersiz alıcı kaynağı")

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

        fair_names: list[str] = []
        if source_type == "manual":
            recipient_summary = self._preview_manual(command)
        else:
            recipient_summary, fair_names = self._preview_fair_list(command)

        mail = self._render_mail(
            command=command,
            template_name=template.name,
            template_subject=template.subject,
            template_body_html=template.body_html,
            template_body_text=template.body_text,
            smtp_name=smtp.name,
            recipients=recipient_summary.recipients,
            fallback_fair_name=fair_names[0] if fair_names else "",
        )

        return BulkEmailOperationPreviewResult(recipients=recipient_summary, mail=mail)

    def _preview_manual(
        self, command: PreviewBulkEmailOperationCommand
    ) -> BulkEmailOperationRecipientSummary:
        excel_tokens: list[str] = []
        if command.excel_bytes:
            try:
                excel_tokens = extract_email_tokens_from_xlsx(command.excel_bytes)
            except InvalidImportFileError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise InvalidImportFileError("Excel dosyası okunamadı") from exc

        manual_text = (command.manual_emails or "").strip()
        if not manual_text and not excel_tokens:
            raise ValueError("Excel dosyası yükleyin veya en az bir e-posta girin.")

        result = resolve_manual_and_excel_emails(
            manual_emails_text=manual_text,
            excel_email_tokens=excel_tokens,
        )
        return BulkEmailOperationRecipientSummary(
            source_type="manual",
            total_found=result.total_found,
            valid_email_count=result.valid_email_count,
            duplicate_count=result.duplicate_count,
            invalid_count=result.invalid_count,
            deduped_recipient_count=result.deduped_recipient_count,
            skipped_count=result.skipped_count,
            selected_fair_count=None,
            selected_fair_names=None,
            total_customers=None,
            total_contacts=None,
            recipients=result.recipients,
        )

    def _preview_fair_list(
        self, command: PreviewBulkEmailOperationCommand
    ) -> tuple[BulkEmailOperationRecipientSummary, list[str]]:
        fair_ids = list(command.fair_ids or [])
        if not fair_ids:
            raise ValueError("En az bir fuar seçin.")

        fair_names: list[str] = []
        for fair_id in fair_ids:
            fair = self._fair_repository.get_by_id(command.organization_id, fair_id)
            if fair is None:
                raise FairNotFoundError("Fair not found")
            if fair.deleted_at is not None:
                raise FairNotEligibleForBulkEmailError(
                    "Arşivlenmiş fuar için toplu mail gönderilemez."
                )
            fair_names.append(fair.name)

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
        recipients = [resolved_to_wizard_recipient(item) for item in preview.recipients]
        return (
            BulkEmailOperationRecipientSummary(
                source_type="fair_list",
                total_found=None,
                valid_email_count=preview.valid_email_count,
                duplicate_count=None,
                invalid_count=None,
                deduped_recipient_count=preview.deduped_recipient_count,
                skipped_count=preview.skipped_count,
                selected_fair_count=len(fair_ids),
                selected_fair_names=fair_names,
                total_customers=preview.total_customers,
                total_contacts=preview.total_contacts,
                recipients=recipients,
            ),
            fair_names,
        )

    def _render_mail(
        self,
        *,
        command: PreviewBulkEmailOperationCommand,
        template_name: str,
        template_subject: str,
        template_body_html: str | None,
        template_body_text: str | None,
        smtp_name: str,
        recipients: list[WizardPreviewRecipient],
        fallback_fair_name: str,
    ) -> BulkEmailOperationMailPreview:
        will_send = [item for item in recipients if item.status == "will_send"]
        sample = will_send[0] if will_send else None
        variables = self._build_variables(
            organization_id=command.organization_id,
            sample=sample,
            fallback_fair_name=fallback_fair_name,
        )
        try:
            rendered_subject = self._renderer.render(template_subject, variables)
            rendered_body_html = (
                self._renderer.render(template_body_html, variables) if template_body_html else None
            )
            rendered_body_text = (
                self._renderer.render(template_body_text, variables) if template_body_text else None
            )
        except MailTemplateRenderError as exc:
            raise MailTemplateRenderError(
                "Mail şablonu render edilirken hata oluştu. Değişkenleri kontrol edin."
            ) from exc

        final_subject = rendered_subject
        if command.subject_override is not None and command.subject_override.strip():
            final_subject = command.subject_override.strip()

        return BulkEmailOperationMailPreview(
            template_id=command.template_id,
            template_name=template_name,
            smtp_account_id=command.smtp_account_id,
            smtp_account_name=smtp_name,
            rendered_subject=final_subject,
            body_html=rendered_body_html,
            body_text=rendered_body_text,
        )

    def _build_variables(
        self,
        *,
        organization_id: UUID,
        sample: WizardPreviewRecipient | None,
        fallback_fair_name: str,
    ) -> dict[str, str]:
        if sample is None:
            return build_render_variables(fair_name=fallback_fair_name, customer_name="")

        contact_first_name = ""
        contact_last_name = ""
        contact_title = ""
        if sample.contact_id is not None:
            contact = self._recipient_loader.load_contact(organization_id, sample.contact_id)
            if contact is not None:
                contact_first_name = contact.first_name
                contact_last_name = contact.last_name
                contact_title = contact.title or ""

        hall = ""
        stand = ""
        if sample.participation_id is not None:
            participation = self._recipient_loader.load_participation_by_id(
                organization_id,
                sample.participation_id,
            )
            if participation is not None:
                hall = participation.hall or ""
                stand = participation.stand or ""

        return build_render_variables(
            fair_name=sample.fair_name or fallback_fair_name,
            customer_name=sample.company_name or "",
            contact_first_name=contact_first_name,
            contact_last_name=contact_last_name,
            contact_title=contact_title,
            hall=hall,
            stand=stand,
        )

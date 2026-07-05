from dataclasses import dataclass

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fair_emails.application.commands import PreviewBulkEmailCommand
from app.modules.fair_emails.application.recipient_resolution import build_render_variables
from app.modules.fair_emails.application.recipient_service import FairBulkEmailRecipientService
from app.modules.fair_emails.domain.exceptions import (
    FairBulkEmailRecipientNotFoundError,
    FairNotEligibleForBulkEmailError,
)
from app.modules.fair_emails.domain.value_objects import ResolvedRecipient
from app.modules.fair_emails.infrastructure.recipient_loader import FairBulkEmailRecipientLoader
from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository
from app.modules.mail_templates.domain.exceptions import (
    MailTemplateAlreadyDeletedError,
    MailTemplateInactiveForTestError,
    MailTemplateNotFoundError,
    MailTemplateRenderError,
)
from app.modules.mail_templates.domain.ports import MailTemplateRepository, MailTemplateRenderer

PERMISSION_PREVIEW = "fair_crm.fair_emails.preview"
INACTIVE_TEMPLATE_MESSAGE = "Pasif mail şablonu ile toplu mail gönderilemez."


@dataclass(frozen=True)
class BulkEmailContentPreviewResult:
    subject: str
    body_html: str | None
    body_text: str | None
    sample_recipient: ResolvedRecipient
    total_send_count: int


class PreviewFairBulkEmailUseCase:
    def __init__(
        self,
        fair_repository: FairRepository,
        template_repository: MailTemplateRepository,
        renderer: MailTemplateRenderer,
        recipient_service: FairBulkEmailRecipientService,
        recipient_loader: FairBulkEmailRecipientLoader,
        authorization: AuthorizationPort,
    ) -> None:
        self._fair_repository = fair_repository
        self._template_repository = template_repository
        self._renderer = renderer
        self._recipient_service = recipient_service
        self._recipient_loader = recipient_loader
        self._authorization = authorization

    def execute(self, command: PreviewBulkEmailCommand) -> BulkEmailContentPreviewResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_PREVIEW,
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

        preview = self._recipient_service.preview(
            command.organization_id,
            command.fair_id,
            command.recipient_options,
        )
        will_send = [item for item in preview.recipients if item.status == "will_send"]
        if not will_send:
            raise FairBulkEmailRecipientNotFoundError("Gönderilecek alıcı bulunamadı.")

        sample = self._resolve_sample(will_send, command.sample_recipient_key)
        variables = self._build_variables(command.organization_id, fair.name, sample)
        try:
            rendered_subject = self._renderer.render(template.subject, variables)
            rendered_body_html = (
                self._renderer.render(template.body_html, variables) if template.body_html else None
            )
            rendered_body_text = (
                self._renderer.render(template.body_text, variables) if template.body_text else None
            )
        except MailTemplateRenderError as exc:
            raise MailTemplateRenderError(
                "Mail şablonu render edilirken hata oluştu. Değişkenleri kontrol edin."
            ) from exc

        final_subject = rendered_subject
        if command.subject_override is not None and command.subject_override.strip():
            final_subject = command.subject_override.strip()

        return BulkEmailContentPreviewResult(
            subject=final_subject,
            body_html=rendered_body_html,
            body_text=rendered_body_text,
            sample_recipient=sample,
            total_send_count=len(will_send),
        )

    def _resolve_sample(
        self,
        will_send: list[ResolvedRecipient],
        sample_recipient_key: str | None,
    ) -> ResolvedRecipient:
        if sample_recipient_key:
            for item in will_send:
                if item.recipient_key == sample_recipient_key:
                    return item
            raise FairBulkEmailRecipientNotFoundError("Örnek alıcı bulunamadı.")
        return will_send[0]

    def _build_variables(self, organization_id, fair_name: str, sample: ResolvedRecipient) -> dict[str, str]:
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
        participation = self._recipient_loader.load_participation_by_id(
            organization_id,
            sample.participation_id,
        )
        if participation is not None:
            hall = participation.hall or ""
            stand = participation.stand or ""

        return build_render_variables(
            fair_name=fair_name,
            customer_name=sample.company_name,
            contact_first_name=contact_first_name,
            contact_last_name=contact_last_name,
            contact_title=contact_title,
            hall=hall,
            stand=stand,
        )

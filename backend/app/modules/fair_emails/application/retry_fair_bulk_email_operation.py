"""Retry handler for failed fair bulk email mail send operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.contacts.infrastructure.persistence.models import ContactModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fair_emails.application.recipient_resolution import build_render_variables
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailOutboxModel
from app.modules.fair_emails.infrastructure.recipient_loader import FairBulkEmailRecipientLoader
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    FairEmailBatchRecord,
    SqlAlchemyFairEmailBatchRepository,
)
from app.modules.mail_templates.domain.exceptions import MailTemplateRenderError
from app.modules.mail_templates.infrastructure.repositories.mail_template_repository import (
    SqlAlchemyMailTemplateRepository,
)
from app.modules.mail_templates.infrastructure.template_renderer import JinjaMailTemplateRenderer
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.shared.consent import CONSENT_ERROR_CODE


class FairBulkEmailOperationRetryHandler:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._batch_repository = SqlAlchemyFairEmailBatchRepository(session)
        self._template_repository = SqlAlchemyMailTemplateRepository(session)
        self._recipient_loader = FairBulkEmailRecipientLoader(session)
        self._renderer = JinjaMailTemplateRenderer()

    def get_outbox_for_operation(
        self,
        organization_id: UUID,
        operation_id: UUID,
    ) -> FairEmailOutboxModel | None:
        return self._batch_repository.get_outbox_by_mail_send_operation_id(
            organization_id,
            operation_id,
        )

    def get_batch(
        self,
        organization_id: UUID,
        batch_id: UUID,
    ) -> FairEmailBatchRecord | None:
        return self._batch_repository.get_batch(organization_id, batch_id)

    def prepare_outbox_for_retry(self, outbox_id: UUID) -> None:
        self._batch_repository.prepare_outbox_for_retry(outbox_id)

    def validate_consent(self, organization_id: UUID, outbox: FairEmailOutboxModel) -> None:
        if outbox.customer_id is None:
            # Manual/excel recipients are outside CRM consent tracking.
            return
        customer = (
            self._session.query(CustomerModel)
            .filter(
                CustomerModel.organization_id == organization_id,
                CustomerModel.id == outbox.customer_id,
            )
            .one_or_none()
        )
        if customer is None or not customer.email_allowed:
            raise SmtpMailDeliveryError(
                "Customer email consent disabled",
                error_type=CONSENT_ERROR_CODE,
            )
        if outbox.contact_id is not None:
            contact = (
                self._session.query(ContactModel)
                .filter(
                    ContactModel.organization_id == organization_id,
                    ContactModel.id == outbox.contact_id,
                )
                .one_or_none()
            )
            if contact is None or not contact.email_allowed:
                raise SmtpMailDeliveryError(
                    "Contact email consent disabled",
                    error_type=CONSENT_ERROR_CODE,
                )

    def build_send_payload(
        self,
        organization_id: UUID,
        *,
        batch: FairEmailBatchRecord,
        outbox: FairEmailOutboxModel,
    ) -> tuple[str, str | None, str | None]:
        template = self._template_repository.get_by_id(organization_id, batch.template_id)
        if template is None or template.deleted_at is not None:
            raise SmtpMailDeliveryError(
                "Mail template not found",
                error_type="MailTemplateNotFound",
            )
        if not template.is_active:
            raise SmtpMailDeliveryError(
                "Mail template is inactive",
                error_type="InactiveTemplate",
            )

        fair_name = self._load_fair_name(organization_id, batch.fair_id)
        variables = self._build_variables(organization_id, fair_name, outbox)
        try:
            rendered_subject = self._renderer.render(template.subject, variables)
            rendered_body_html = (
                self._renderer.render(template.body_html, variables) if template.body_html else None
            )
            rendered_body_text = (
                self._renderer.render(template.body_text, variables) if template.body_text else None
            )
        except MailTemplateRenderError as exc:
            raise SmtpMailDeliveryError(
                "Mail şablonu render edilemedi.",
                error_type="template_render_error",
            ) from exc

        final_subject = batch.subject_override or rendered_subject
        body_text = rendered_body_text or final_subject
        return final_subject, body_text, rendered_body_html

    def mark_outbox_sending(self, outbox_id: UUID) -> None:
        self._batch_repository.mark_outbox_sending(outbox_id)

    def sync_outbox_sent(
        self,
        outbox_id: UUID,
        *,
        subject: str,
        body_html: str | None,
        body_text: str | None,
    ) -> None:
        self._batch_repository.update_outbox_sent(
            outbox_id,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
        )

    def sync_outbox_failed(self, outbox_id: UUID, *, message: str) -> None:
        self._batch_repository.update_outbox_failed(outbox_id, message=message)

    def _load_fair_name(self, organization_id: UUID, fair_id: UUID | None) -> str:
        if fair_id is None:
            return ""
        from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository

        fair = SqlAlchemyFairRepository(self._session).get_by_id(organization_id, fair_id)
        return fair.name if fair else ""

    def _build_variables(self, organization_id: UUID, fair_name: str, outbox: FairEmailOutboxModel) -> dict[str, str]:
        contact_first_name = ""
        contact_last_name = ""
        contact_title = ""
        if outbox.contact_id is not None:
            contact = self._recipient_loader.load_contact(organization_id, outbox.contact_id)
            if contact is not None:
                contact_first_name = contact.first_name
                contact_last_name = contact.last_name
                contact_title = contact.title or ""

        hall = ""
        stand = ""
        if outbox.participation_id is not None:
            participation = self._recipient_loader.load_participation_by_id(
                organization_id,
                outbox.participation_id,
            )
            if participation is not None:
                hall = participation.hall or ""
                stand = participation.stand or ""

        return build_render_variables(
            fair_name=fair_name,
            customer_name=outbox.company_name or "",
            contact_first_name=contact_first_name,
            contact_last_name=contact_last_name,
            contact_title=contact_title,
            hall=hall,
            stand=stand,
        )

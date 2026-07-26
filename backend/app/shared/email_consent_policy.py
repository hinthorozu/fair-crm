"""Central EmailConsentPolicy — CRM email_allowed checks for all send flows."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.contacts.infrastructure.persistence.models import ContactModel
from app.modules.customers.infrastructure.persistence.communication_models import CustomerEmailModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.shared.consent import (
    CONSENT_ERROR_CODE,
    EmailConsentBlockedError,
    EmailConsentDecision,
    evaluate_email_consent_flags,
)
from app.shared.email import normalize_bulk_recipient_email
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError


class EmailConsentPolicy:
    """Single policy used before MSO enqueue and again in worker/dispatcher."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def evaluate(
        self,
        organization_id: UUID,
        *,
        email: str | None = None,
        customer_id: UUID | None = None,
        contact_id: UUID | None = None,
    ) -> EmailConsentDecision:
        customer_flags: dict[UUID, bool] = {}
        contact_flags: dict[UUID, bool] = {}

        if customer_id is not None:
            customer = self._load_customer(organization_id, customer_id)
            if customer is not None:
                customer_flags[customer.id] = bool(customer.email_allowed)

        if contact_id is not None:
            contact = self._load_contact(organization_id, contact_id)
            if contact is not None:
                contact_flags[contact.id] = bool(contact.email_allowed)
                parent = self._load_customer(organization_id, contact.customer_id)
                if parent is not None:
                    customer_flags[parent.id] = bool(parent.email_allowed)

        normalized = normalize_bulk_recipient_email(email)
        if normalized:
            self._collect_matches_by_email(
                organization_id,
                normalized,
                customer_flags=customer_flags,
                contact_flags=contact_flags,
            )

        return evaluate_email_consent_flags(
            customer_email_allowed_flags=list(customer_flags.values()),
            contact_email_allowed_flags=list(contact_flags.values()),
        )

    def ensure_allowed(
        self,
        organization_id: UUID,
        *,
        email: str | None = None,
        customer_id: UUID | None = None,
        contact_id: UUID | None = None,
    ) -> EmailConsentDecision:
        decision = self.evaluate(
            organization_id,
            email=email,
            customer_id=customer_id,
            contact_id=contact_id,
        )
        if not decision.allowed:
            raise EmailConsentBlockedError(decision)
        return decision

    def ensure_allowed_or_delivery_error(
        self,
        organization_id: UUID,
        *,
        email: str | None = None,
        customer_id: UUID | None = None,
        contact_id: UUID | None = None,
    ) -> EmailConsentDecision:
        """Same as ensure_allowed but raises SmtpMailDeliveryError for worker paths."""
        try:
            return self.ensure_allowed(
                organization_id,
                email=email,
                customer_id=customer_id,
                contact_id=contact_id,
            )
        except EmailConsentBlockedError as exc:
            raise SmtpMailDeliveryError(
                exc.decision.message or "Email consent blocked",
                error_type=CONSENT_ERROR_CODE,
                retryable=False,
            ) from exc

    def _load_customer(self, organization_id: UUID, customer_id: UUID) -> CustomerModel | None:
        return (
            self._session.query(CustomerModel)
            .filter(
                CustomerModel.organization_id == organization_id,
                CustomerModel.id == customer_id,
                CustomerModel.deleted_at.is_(None),
            )
            .one_or_none()
        )

    def _load_contact(self, organization_id: UUID, contact_id: UUID) -> ContactModel | None:
        return (
            self._session.query(ContactModel)
            .filter(
                ContactModel.organization_id == organization_id,
                ContactModel.id == contact_id,
                ContactModel.deleted_at.is_(None),
            )
            .one_or_none()
        )

    def _collect_matches_by_email(
        self,
        organization_id: UUID,
        normalized_email: str,
        *,
        customer_flags: dict[UUID, bool],
        contact_flags: dict[UUID, bool],
    ) -> None:
        email_rows = (
            self._session.query(CustomerEmailModel, CustomerModel)
            .join(CustomerModel, CustomerModel.id == CustomerEmailModel.customer_id)
            .filter(
                CustomerEmailModel.organization_id == organization_id,
                CustomerModel.organization_id == organization_id,
                CustomerModel.deleted_at.is_(None),
                func.lower(CustomerEmailModel.email) == normalized_email,
            )
            .all()
        )
        for email_row, customer in email_rows:
            stored = normalize_bulk_recipient_email(email_row.email)
            if stored != normalized_email:
                continue
            customer_flags[customer.id] = bool(customer.email_allowed)

        contact_rows = (
            self._session.query(ContactModel, CustomerModel)
            .join(CustomerModel, CustomerModel.id == ContactModel.customer_id)
            .filter(
                ContactModel.organization_id == organization_id,
                CustomerModel.organization_id == organization_id,
                ContactModel.deleted_at.is_(None),
                CustomerModel.deleted_at.is_(None),
                ContactModel.email.isnot(None),
                func.lower(ContactModel.email) == normalized_email,
            )
            .all()
        )
        for contact, customer in contact_rows:
            stored = normalize_bulk_recipient_email(contact.email)
            if stored != normalized_email:
                continue
            contact_flags[contact.id] = bool(contact.email_allowed)
            customer_flags[customer.id] = bool(customer.email_allowed)

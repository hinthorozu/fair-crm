from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.contacts.infrastructure.persistence.models import ContactModel
from app.modules.customers.infrastructure.persistence.communication_models import CustomerEmailModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fair_emails.application.recipient_resolution import iter_valid_emails
from app.modules.fair_emails.domain.value_objects import RawRecipientCandidate, RecipientOptions
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.shared.email import is_valid_email_address


@dataclass(frozen=True)
class ParticipationContext:
    participation_id: UUID
    customer_id: UUID
    company_name: str
    customer_active: bool
    customer_email_allowed: bool
    hall: str | None
    stand: str | None
    fair_id: UUID | None = None
    fair_name: str | None = None


@dataclass(frozen=True)
class ContactContext:
    contact_id: UUID
    customer_id: UUID
    first_name: str
    last_name: str
    title: str | None
    email: str | None
    is_active: bool


@dataclass(frozen=True)
class ParticipationFilters:
    country: str | None = None
    city: str | None = None
    company_name_contains: str | None = None


class FairBulkEmailRecipientLoader:
    def __init__(self, session: Session) -> None:
        self._session = session

    def load_participations(self, organization_id: UUID, fair_id: UUID) -> list[ParticipationContext]:
        return self.load_participations_for_fairs(organization_id, [fair_id])

    def load_participations_for_fairs(
        self,
        organization_id: UUID,
        fair_ids: list[UUID],
        filters: ParticipationFilters | None = None,
    ) -> list[ParticipationContext]:
        if not fair_ids:
            return []

        query = (
            self._session.query(CustomerFairParticipationModel, CustomerModel, FairModel)
            .join(CustomerModel, CustomerFairParticipationModel.customer_id == CustomerModel.id)
            .join(FairModel, CustomerFairParticipationModel.fair_id == FairModel.id)
            .filter(
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.fair_id.in_(fair_ids),
                CustomerFairParticipationModel.deleted_at.is_(None),
                CustomerModel.deleted_at.is_(None),
                FairModel.deleted_at.is_(None),
            )
        )

        applied = filters or ParticipationFilters()
        country = (applied.country or "").strip()
        city = (applied.city or "").strip()
        company = (applied.company_name_contains or "").strip()
        if country:
            query = query.filter(CustomerModel.country.ilike(f"%{country}%"))
        if city:
            query = query.filter(CustomerModel.city.ilike(f"%{city}%"))
        if company:
            query = query.filter(CustomerModel.display_name.ilike(f"%{company}%"))

        rows = query.all()
        return [
            ParticipationContext(
                participation_id=participation.id,
                customer_id=customer.id,
                company_name=customer.display_name,
                customer_active=customer.deleted_at is None,
                customer_email_allowed=customer.email_allowed,
                hall=participation.hall,
                stand=participation.stand,
                fair_id=fair.id,
                fair_name=fair.name,
            )
            for participation, customer, fair in rows
        ]

    def load_customer_email_candidates(
        self,
        organization_id: UUID,
        participations: list[ParticipationContext],
        options: RecipientOptions,
    ) -> list[RawRecipientCandidate]:
        if not options.include_customer_emails or not participations:
            return []

        # Preserve multi-fair participation rows so each fair can appear in preview;
        # email dedupe still collapses identical addresses when enabled.
        participation_by_customer: dict[UUID, list[ParticipationContext]] = {}
        for item in participations:
            participation_by_customer.setdefault(item.customer_id, []).append(item)

        customer_ids = list(participation_by_customer.keys())
        email_rows = (
            self._session.query(CustomerEmailModel)
            .filter(CustomerEmailModel.customer_id.in_(customer_ids))
            .order_by(CustomerEmailModel.is_primary.desc(), CustomerEmailModel.created_at.asc())
            .all()
        )

        candidates: list[RawRecipientCandidate] = []
        for email_row in email_rows:
            for participation in participation_by_customer[email_row.customer_id]:
                email = (email_row.email or "").strip().lower()
                candidates.append(
                    RawRecipientCandidate(
                        recipient_name=participation.company_name,
                        company_name=participation.company_name,
                        email=email,
                        source="customer",
                        customer_id=participation.customer_id,
                        contact_id=None,
                        participation_id=participation.participation_id,
                        is_active=participation.customer_active,
                        email_valid=is_valid_email_address(email),
                        customer_email_allowed=participation.customer_email_allowed,
                        contact_email_allowed=True,
                        fair_id=participation.fair_id,
                        fair_name=participation.fair_name,
                    )
                )
        return candidates

    def load_contact_email_candidates(
        self,
        organization_id: UUID,
        participations: list[ParticipationContext],
        options: RecipientOptions,
    ) -> list[RawRecipientCandidate]:
        if not options.include_contact_emails or not participations:
            return []

        participation_by_customer: dict[UUID, list[ParticipationContext]] = {}
        for item in participations:
            participation_by_customer.setdefault(item.customer_id, []).append(item)

        customer_ids = list(participation_by_customer.keys())
        contact_rows = (
            self._session.query(ContactModel)
            .filter(
                ContactModel.organization_id == organization_id,
                ContactModel.customer_id.in_(customer_ids),
                ContactModel.deleted_at.is_(None),
            )
            .all()
        )

        candidates: list[RawRecipientCandidate] = []
        for contact in contact_rows:
            for participation in participation_by_customer[contact.customer_id]:
                recipient_name = f"{contact.first_name} {contact.last_name}".strip()
                for email in iter_valid_emails(contact.email):
                    candidates.append(
                        RawRecipientCandidate(
                            recipient_name=recipient_name or None,
                            company_name=participation.company_name,
                            email=email,
                            source="contact",
                            customer_id=participation.customer_id,
                            contact_id=contact.id,
                            participation_id=participation.participation_id,
                            is_active=participation.customer_active and contact.is_active,
                            email_valid=True,
                            customer_email_allowed=participation.customer_email_allowed,
                            contact_email_allowed=contact.email_allowed,
                            fair_id=participation.fair_id,
                            fair_name=participation.fair_name,
                        )
                    )
                if contact.email and not iter_valid_emails(contact.email):
                    candidates.append(
                        RawRecipientCandidate(
                            recipient_name=recipient_name or None,
                            company_name=participation.company_name,
                            email=contact.email.strip(),
                            source="contact",
                            customer_id=participation.customer_id,
                            contact_id=contact.id,
                            participation_id=participation.participation_id,
                            is_active=participation.customer_active and contact.is_active,
                            email_valid=False,
                            customer_email_allowed=participation.customer_email_allowed,
                            contact_email_allowed=contact.email_allowed,
                            fair_id=participation.fair_id,
                            fair_name=participation.fair_name,
                        )
                    )
        return candidates

    def load_participation_by_id(
        self, organization_id: UUID, participation_id: UUID
    ) -> ParticipationContext | None:
        row = (
            self._session.query(CustomerFairParticipationModel, CustomerModel, FairModel)
            .join(CustomerModel, CustomerFairParticipationModel.customer_id == CustomerModel.id)
            .join(FairModel, CustomerFairParticipationModel.fair_id == FairModel.id)
            .filter(
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.id == participation_id,
                CustomerFairParticipationModel.deleted_at.is_(None),
                CustomerModel.deleted_at.is_(None),
            )
            .one_or_none()
        )
        if row is None:
            return None
        participation, customer, fair = row
        return ParticipationContext(
            participation_id=participation.id,
            customer_id=customer.id,
            company_name=customer.display_name,
            customer_active=customer.deleted_at is None,
            customer_email_allowed=customer.email_allowed,
            hall=participation.hall,
            stand=participation.stand,
            fair_id=fair.id,
            fair_name=fair.name,
        )

    def load_contact(self, organization_id: UUID, contact_id: UUID) -> ContactContext | None:
        model = (
            self._session.query(ContactModel)
            .filter(
                ContactModel.organization_id == organization_id,
                ContactModel.id == contact_id,
                ContactModel.deleted_at.is_(None),
            )
            .one_or_none()
        )
        if model is None:
            return None
        return ContactContext(
            contact_id=model.id,
            customer_id=model.customer_id,
            first_name=model.first_name,
            last_name=model.last_name,
            title=model.title,
            email=model.email,
            is_active=model.is_active,
        )

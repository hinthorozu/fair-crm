from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from app.modules.customers.application.communication_parsing import (
    emails_from_scalar,
    phones_from_scalar,
    websites_from_scalar,
)
from app.modules.customers.domain.communication_entities import CustomerCommunications
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)


class CustomerCommunicationSyncService:
    def __init__(self, repository: SqlAlchemyCustomerCommunicationRepository) -> None:
        self._repository = repository

    def sync_from_value_lists(
        self,
        *,
        organization_id: UUID,
        customer_id: UUID,
        now: datetime,
        phones: list[str] | None = None,
        emails: list[str] | None = None,
        websites: list[str] | None = None,
        sync_phone: bool = False,
        sync_email: bool = False,
        sync_website: bool = False,
    ) -> CustomerCommunications:
        if sync_phone:
            self._repository.replace_phones(
                organization_id=organization_id,
                customer_id=customer_id,
                phones=phones or [],
                now=now,
            )
        if sync_email:
            normalized_emails = emails or []
            self._repository.replace_emails(
                organization_id=organization_id,
                customer_id=customer_id,
                emails=normalized_emails,
                now=now,
            )
            if not normalized_emails:
                self._reset_enrichment_state_if_customer_has_no_email(
                    organization_id=organization_id,
                    customer_id=customer_id,
                )
        if sync_website:
            self._repository.replace_websites(
                organization_id=organization_id,
                customer_id=customer_id,
                websites=websites or [],
                now=now,
            )

        return self._repository.load_for_customer(customer_id)

    def sync_from_scalar_fields(
        self,
        *,
        organization_id: UUID,
        customer_id: UUID,
        now: datetime,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        website: Optional[str] = None,
        sync_phone: bool = False,
        sync_email: bool = False,
        sync_website: bool = False,
    ) -> CustomerCommunications:
        return self.sync_from_value_lists(
            organization_id=organization_id,
            customer_id=customer_id,
            now=now,
            phones=phones_from_scalar(phone) if sync_phone else None,
            emails=emails_from_scalar(email) if sync_email else None,
            websites=websites_from_scalar(website) if sync_website else None,
            sync_phone=sync_phone,
            sync_email=sync_email,
            sync_website=sync_website,
        )

    def load_for_customer(self, customer_id: UUID) -> CustomerCommunications:
        return self._repository.load_for_customer(customer_id)

    def _reset_enrichment_state_if_customer_has_no_email(
        self,
        *,
        organization_id: UUID,
        customer_id: UUID,
    ) -> None:
        from app.modules.scraper.services.customer_enrichment_state_service import (
            reset_enrichment_state_if_customer_has_no_email,
        )

        reset_enrichment_state_if_customer_has_no_email(
            self._repository.session,
            organization_id=organization_id,
            customer_id=customer_id,
        )

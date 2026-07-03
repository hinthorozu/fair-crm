"""Build merge preview with CRM context for import rows."""

from uuid import UUID

from app.modules.contacts.domain.entities import Contact
from app.modules.contacts.domain.ports import ContactRepository
from app.modules.customers.application.communication_parsing import api_scalar_fields_from_communications
from app.modules.customers.application.customer_communication_sync import CustomerCommunicationSyncService
from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.services.merge_preview import build_merge_preview
from app.modules.participations.domain.entities import CustomerFairParticipation
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)


class MergePreviewBuilder:
    def __init__(
        self,
        customer_repository: CustomerRepository,
        communication_sync: CustomerCommunicationSyncService,
        participation_repository: SqlAlchemyParticipationRepository,
        contact_repository: ContactRepository,
    ) -> None:
        self._customer_repository = customer_repository
        self._communication_sync = communication_sync
        self._participation_repository = participation_repository
        self._contact_repository = contact_repository

    def build_for_row(
        self,
        organization_id: UUID,
        batch: ImportBatch,
        row: ImportRow,
    ) -> dict:
        customer: Customer | None = None
        participation: CustomerFairParticipation | None = None
        contact: Contact | None = None
        customer_phone: str | None = None
        customer_email: str | None = None
        customer_website: str | None = None

        if row.match_customer_id:
            customer = self._customer_repository.get_by_id(organization_id, row.match_customer_id)
            if customer:
                communications = self._communication_sync.load_for_customer(customer.id)
                customer_phone, customer_email, customer_website, _, _, _ = (
                    api_scalar_fields_from_communications(communications)
                )

        if batch.fair_id and customer:
            participation = self._participation_repository.get_active_by_customer_and_fair(
                organization_id, customer.id, batch.fair_id
            )

        data = row.normalized_data_json or {}
        first_name = data.get("contact_first_name")
        last_name = data.get("contact_last_name")
        if customer and first_name and last_name:
            contact = self._contact_repository.find_by_customer_and_name(
                organization_id,
                customer.id,
                str(first_name).strip().lower(),
                str(last_name).strip().lower(),
            )

        return build_merge_preview(
            row,
            customer=customer,
            customer_phone=customer_phone,
            customer_email=customer_email,
            customer_website=customer_website,
            participation=participation,
            contact=contact,
            fair_id=batch.fair_id,
        )

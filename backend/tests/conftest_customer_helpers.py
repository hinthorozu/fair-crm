"""Shared helpers for creating customers with communication child rows in tests."""

from datetime import UTC, datetime
from uuid import UUID

from app.modules.customers.application.communication_parsing import emails_from_scalar, phones_from_scalar
from app.modules.customers.application.customer_communication_sync import CustomerCommunicationSyncService
from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.value_objects import CustomerSource
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)
from app.modules.customers.infrastructure.repositories.customer_repository import SqlAlchemyCustomerRepository


def create_test_customer(
    db_session,
    organization_id: UUID,
    *,
    display_name: str,
    email: str | None = None,
    phone: str | None = None,
    website: str | None = None,
    country: str | None = None,
    source: CustomerSource = CustomerSource.MANUAL,
) -> Customer:
    now = datetime.now(tz=UTC)
    customer = Customer.create(
        organization_id=organization_id,
        display_name=display_name,
        country=country,
        source=source,
        now=now,
    )
    saved = SqlAlchemyCustomerRepository(db_session).add(customer)
    phones = phones_from_scalar(phone) if phone else []
    emails = emails_from_scalar(email) if email else []
    websites = [website] if website else []
    if phones or emails or websites:
        CustomerCommunicationSyncService(SqlAlchemyCustomerCommunicationRepository(db_session)).sync_from_value_lists(
            customer_id=saved.id,
            organization_id=organization_id,
            phones=phones,
            emails=emails,
            websites=websites,
            now=now,
            sync_phone=True,
            sync_email=True,
            sync_website=True,
        )
    return saved

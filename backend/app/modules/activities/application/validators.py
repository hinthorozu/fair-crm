from datetime import UTC, datetime
from uuid import UUID

from app.modules.activities.domain.exceptions import (
    ContactCustomerMismatchError,
    ContactNotFoundForActivityError,
)
from app.modules.contacts.domain.ports import ContactRepository
from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.ports import CustomerRepository


def ensure_customer_for_activity(
    customer_repository: CustomerRepository,
    organization_id: UUID,
    customer_id: UUID,
) -> Customer:
    from app.modules.activities.domain.exceptions import (
        CustomerArchivedForActivityError,
        CustomerNotFoundForActivityError,
    )

    customer = customer_repository.get_by_id_including_archived(organization_id, customer_id)
    if customer is None:
        raise CustomerNotFoundForActivityError("Customer not found")
    if customer.is_merge_deleted():
        raise CustomerArchivedForActivityError("Customer is deleted")
    if customer.is_archived():
        raise CustomerArchivedForActivityError("Customer is archived")
    return customer


def validate_contact_for_activity(
    contact_repository: ContactRepository,
    organization_id: UUID,
    customer_id: UUID,
    contact_id: UUID | None,
) -> None:
    if contact_id is None:
        return

    contact = contact_repository.get_by_id(organization_id, contact_id)
    if contact is None:
        raise ContactNotFoundForActivityError("Contact not found")
    if contact.customer_id != customer_id:
        raise ContactCustomerMismatchError("Contact does not belong to this customer")

from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.contacts.application.commands import CreateContactCommand, ContactResult
from app.modules.contacts.application.mappers import contact_to_result
from app.modules.contacts.domain.entities import Contact
from app.modules.contacts.domain.exceptions import CustomerArchivedForContactError
from app.modules.contacts.domain.ports import ContactRepository
from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.ports import CustomerRepository

PERMISSION_CREATE = "fair_crm.contacts.create"


def _ensure_customer_for_contact(
    customer_repository: CustomerRepository,
    organization_id: UUID,
    customer_id: UUID,
) -> Customer:
    from app.modules.contacts.domain.exceptions import CustomerNotFoundForContactError

    customer = customer_repository.get_by_id_including_archived(organization_id, customer_id)
    if customer is None:
        raise CustomerNotFoundForContactError("Customer not found")
    if customer.is_merge_deleted():
        raise CustomerArchivedForContactError("Customer is deleted")
    if customer.is_archived():
        raise CustomerArchivedForContactError("Customer is archived")
    return customer


class CreateContactUseCase:
    def __init__(
        self,
        contact_repository: ContactRepository,
        customer_repository: CustomerRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._contact_repository = contact_repository
        self._customer_repository = customer_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: CreateContactCommand) -> ContactResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        _ensure_customer_for_contact(
            self._customer_repository, command.organization_id, command.customer_id
        )

        now = datetime.now(tz=UTC)
        contact = Contact.create(
            organization_id=command.organization_id,
            customer_id=command.customer_id,
            first_name=command.first_name,
            last_name=command.last_name,
            title=command.title,
            department=command.department,
            email=command.email,
            phone=command.phone,
            mobile_phone=command.mobile_phone,
            linkedin=command.linkedin,
            notes=command.notes,
            is_primary=command.is_primary,
            is_active=command.is_active,
            now=now,
        )

        if contact.is_primary:
            self._contact_repository.clear_primary_for_customer(
                command.organization_id, command.customer_id
            )

        saved = self._contact_repository.add(contact)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.contact.created",
            resource_type="contact",
            resource_id=str(saved.id),
            new_values={"full_name": saved.full_name, "customer_id": str(saved.customer_id)},
            metadata={"user_id": str(command.user_id)},
        )

        return contact_to_result(saved)

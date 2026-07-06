from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.contacts.application.commands import ContactResult, UpdateContactCommand
from app.modules.contacts.application.mappers import contact_to_result
from app.modules.contacts.domain.exceptions import ContactNotFoundError
from app.modules.contacts.domain.ports import ContactRepository

PERMISSION_UPDATE = "fair_crm.contacts.update"


class UpdateContactUseCase:
    def __init__(
        self,
        repository: ContactRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: UpdateContactCommand) -> ContactResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        contact = self._repository.get_by_id(command.organization_id, command.contact_id)
        if contact is None:
            raise ContactNotFoundError("Contact not found")

        now = datetime.now(tz=UTC)
        contact.update_fields(
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
            email_allowed=command.email_allowed,
            sms_allowed=command.sms_allowed,
            consent_note=command.consent_note,
            now=now,
        )

        if command.is_primary is True:
            self._repository.clear_primary_for_customer(
                command.organization_id,
                contact.customer_id,
                exclude_contact_id=contact.id,
            )

        saved = self._repository.update(contact)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.contact.updated",
            resource_type="contact",
            resource_id=str(saved.id),
            new_values={"full_name": saved.full_name},
            metadata={"user_id": str(command.user_id)},
        )

        return contact_to_result(saved)

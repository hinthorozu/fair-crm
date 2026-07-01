from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.contacts.application.commands import ContactResult, DeleteContactCommand
from app.modules.contacts.application.mappers import contact_to_result
from app.modules.contacts.domain.exceptions import ContactNotFoundError
from app.modules.contacts.domain.ports import ContactRepository

PERMISSION_DELETE = "fair_crm.contacts.delete"


class DeleteContactUseCase:
    def __init__(
        self,
        repository: ContactRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: DeleteContactCommand) -> ContactResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_DELETE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        contact = self._repository.get_by_id(command.organization_id, command.contact_id)
        if contact is None:
            raise ContactNotFoundError("Contact not found")

        now = datetime.now(tz=UTC)
        contact.soft_delete(now=now)
        saved = self._repository.update(contact)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.contact.deleted",
            resource_type="contact",
            resource_id=str(saved.id),
            metadata={"user_id": str(command.user_id)},
        )

        return contact_to_result(saved)

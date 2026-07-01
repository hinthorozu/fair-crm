from app.modules.contacts.application.commands import ContactResult, GetContactQuery
from app.modules.contacts.application.mappers import contact_to_result
from app.modules.contacts.domain.exceptions import ContactNotFoundError
from app.modules.contacts.domain.ports import ContactRepository


class GetContactUseCase:
    def __init__(self, repository: ContactRepository) -> None:
        self._repository = repository

    def execute(self, query: GetContactQuery) -> ContactResult:
        contact = self._repository.get_by_id(query.organization_id, query.contact_id)
        if contact is None:
            raise ContactNotFoundError("Contact not found")
        return contact_to_result(contact)

from app.core.pagination import normalize_page_params, normalize_sort_direction
from app.modules.contacts.application.commands import ContactListResultDto, ListContactsByCustomerQuery
from app.modules.contacts.application.mappers import contact_to_result
from app.modules.contacts.domain.exceptions import CustomerNotFoundForContactError
from app.modules.contacts.domain.ports import ContactRepository
from app.modules.customers.domain.ports import CustomerRepository


class ListContactsByCustomerUseCase:
    def __init__(
        self,
        contact_repository: ContactRepository,
        customer_repository: CustomerRepository,
    ) -> None:
        self._contact_repository = contact_repository
        self._customer_repository = customer_repository

    def execute(self, query: ListContactsByCustomerQuery) -> ContactListResultDto:
        customer = self._customer_repository.get_by_id_including_archived(
            query.organization_id, query.customer_id
        )
        if customer is None:
            raise CustomerNotFoundForContactError("Customer not found")

        page_params = normalize_page_params(query.page, query.page_size)
        sort_dir = normalize_sort_direction(query.sort_dir)

        result = self._contact_repository.list_by_customer(
            query.organization_id,
            query.customer_id,
            page=page_params.page,
            page_size=page_params.page_size,
            sort_by=query.sort_by,
            sort_dir=sort_dir,
        )

        return ContactListResultDto(
            items=[contact_to_result(item) for item in result.items],
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        )

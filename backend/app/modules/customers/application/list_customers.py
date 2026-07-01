from app.core.pagination import normalize_page_params, normalize_sort_direction
from app.modules.customers.application.commands import CustomerListResultDto, ListCustomersQuery
from app.modules.customers.application.mappers import list_result_to_dto
from app.modules.customers.domain.ports import CustomerRepository

ALLOWED_SORT_FIELDS = frozenset({"created_at", "updated_at", "display_name"})


class ListCustomersUseCase:
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    def execute(self, query: ListCustomersQuery) -> CustomerListResultDto:
        page_params = normalize_page_params(query.page, query.page_size)
        sort_by = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else "created_at"
        sort_dir = normalize_sort_direction(query.sort_dir)

        result = self._repository.list_by_organization(
            query.organization_id,
            status=query.status,
            include_archived=query.include_archived,
            customer_type=query.customer_type,
            search=query.search,
            page=page_params.page,
            page_size=page_params.page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return list_result_to_dto(result)

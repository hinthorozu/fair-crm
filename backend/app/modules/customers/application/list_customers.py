from app.core.pagination import normalize_page_params, normalize_sort_direction
from app.modules.customers.application.commands import CustomerListResultDto, ListCustomersQuery
from app.modules.customers.application.mappers import list_result_to_dto
from app.modules.customers.domain.ports import CustomerRepository

ALLOWED_SORT_FIELDS = frozenset(
    {"created_at", "updated_at", "display_name", "company_name", "country", "city", "email"}
)
DEFAULT_SORT_FIELD = "company_name"
DEFAULT_SORT_DIRECTION = "asc"


class ListCustomersUseCase:
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    def execute(self, query: ListCustomersQuery) -> CustomerListResultDto:
        page_params = normalize_page_params(query.page, query.page_size)
        sort_by = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
        if sort_by == "company_name":
            sort_by = "display_name"
        sort_dir = normalize_sort_direction(query.sort_dir or DEFAULT_SORT_DIRECTION)

        result = self._repository.list_by_organization(
            query.organization_id,
            status=query.status,
            include_archived=query.include_archived,
            customer_type=query.customer_type,
            country=query.country,
            search=query.search,
            page=page_params.page,
            page_size=page_params.page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return list_result_to_dto(result)

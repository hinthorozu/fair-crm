from app.core.pagination import normalize_page_params, normalize_sort_direction
from app.modules.customers.application.commands import CustomerListResultDto, ListCustomersQuery
from app.modules.customers.application.mappers import list_result_to_dto
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)

# Customer name column aliases — all sort by visible display_name (case-insensitive in repo).
CUSTOMER_NAME_SORT_ALIASES = frozenset({"name", "company_name", "display_name"})

ALLOWED_SORT_FIELDS = frozenset(
    {
        "created_at",
        "updated_at",
        "name",
        "display_name",
        "company_name",
        "country",
        "city",
        "email",
        "status",
        "customer_type",
        "phone",
    }
)
DEFAULT_SORT_FIELD = "name"
DEFAULT_SORT_DIRECTION = "asc"


def resolve_customer_list_sort(sort_by: str) -> str:
    """Map API whitelist field to repository sort key."""
    if sort_by in CUSTOMER_NAME_SORT_ALIASES:
        return "display_name"
    return sort_by


def customer_name_sort_api_field(resolved_db_sort: str) -> str:
    """Canonical sorting.field value for customer name column in list responses."""
    if resolved_db_sort == "display_name":
        return "name"
    return resolved_db_sort


class ListCustomersUseCase:
    def __init__(
        self,
        repository: CustomerRepository,
        communication_repository: SqlAlchemyCustomerCommunicationRepository,
    ) -> None:
        self._repository = repository
        self._communication_repository = communication_repository

    def execute(self, query: ListCustomersQuery) -> CustomerListResultDto:
        page_params = normalize_page_params(query.page, query.page_size)
        requested = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
        sort_by = resolve_customer_list_sort(requested)
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
        customer_ids = [item.id for item in result.items]
        summaries = self._communication_repository.load_list_summaries(customer_ids)
        return list_result_to_dto(result, communication_summaries=summaries)

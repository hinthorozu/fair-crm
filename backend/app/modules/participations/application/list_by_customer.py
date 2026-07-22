from app.core.pagination import normalize_page_params, normalize_sort_direction
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.participations.application.commands import (
    CustomerParticipationListResultDto,
    ListParticipationsByCustomerQuery,
)
from app.modules.participations.application.mappers import customer_row_to_list_item
from app.modules.participations.application.validators import ensure_customer_for_participation
from app.modules.participations.domain.ports import ParticipationRepository

ALLOWED_SORT_FIELDS = frozenset(
    {
        "created_at",
        "updated_at",
        "hall",
        "stand",
        "fair_start_date",
        "fair_name",
        "notes",
    }
)
DEFAULT_SORT_FIELD = "fair_start_date"
DEFAULT_SORT_DIRECTION = "desc"


class ListParticipationsByCustomerUseCase:
    def __init__(
        self,
        participation_repository: ParticipationRepository,
        customer_repository: CustomerRepository,
    ) -> None:
        self._participation_repository = participation_repository
        self._customer_repository = customer_repository

    def execute(self, query: ListParticipationsByCustomerQuery) -> CustomerParticipationListResultDto:
        ensure_customer_for_participation(
            self._customer_repository, query.organization_id, query.customer_id
        )

        page_params = normalize_page_params(query.page, query.page_size)
        sort_by = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
        sort_dir = normalize_sort_direction(query.sort_dir or DEFAULT_SORT_DIRECTION)

        result = self._participation_repository.list_by_customer(
            query.organization_id,
            query.customer_id,
            search=query.search,
            page=page_params.page,
            page_size=page_params.page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

        return CustomerParticipationListResultDto(
            items=[customer_row_to_list_item(row) for row in result.items],
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        )

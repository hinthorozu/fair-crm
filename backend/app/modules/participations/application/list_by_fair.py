from app.core.pagination import normalize_page_params, normalize_sort_direction
from app.modules.participations.application.commands import (
    CustomerParticipationListResultDto,
    FairParticipantListResultDto,
    ListParticipantsByFairQuery,
    ListParticipationsByCustomerQuery,
)
from app.modules.participations.application.mappers import fair_row_to_list_item, resolve_primary_contact_name
from app.modules.participations.application.validators import ensure_fair_for_participation
from app.modules.participations.domain.ports import ParticipationRepository
from app.modules.fairs.domain.ports import FairRepository

ALLOWED_SORT_FIELDS = frozenset(
    {
        "created_at",
        "updated_at",
        "visited_at",
        "hall",
        "stand",
        "participation_status",
        "company_name",
    }
)
DEFAULT_SORT_FIELD = "company_name"
DEFAULT_SORT_DIRECTION = "asc"


class ListParticipantsByFairUseCase:
    def __init__(
        self,
        participation_repository: ParticipationRepository,
        fair_repository: FairRepository,
    ) -> None:
        self._participation_repository = participation_repository
        self._fair_repository = fair_repository

    def execute(self, query: ListParticipantsByFairQuery) -> FairParticipantListResultDto:
        ensure_fair_for_participation(self._fair_repository, query.organization_id, query.fair_id)

        page_params = normalize_page_params(query.page, query.page_size)
        sort_by = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
        sort_dir = normalize_sort_direction(query.sort_dir or DEFAULT_SORT_DIRECTION)

        result = self._participation_repository.list_by_fair(
            query.organization_id,
            query.fair_id,
            search=query.search,
            participation_status=query.participation_status,
            page=page_params.page,
            page_size=page_params.page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

        items = []
        for row in result.items:
            contact_name = resolve_primary_contact_name(
                self._participation_repository,
                query.organization_id,
                row.participation.primary_contact_id,
            )
            items.append(fair_row_to_list_item(row, primary_contact_name=contact_name))

        return FairParticipantListResultDto(
            items=items,
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        )

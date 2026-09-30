from uuid import UUID

from app.core.pagination import normalize_page_params, normalize_sort_direction
from app.modules.fairs.domain.ports import FairRepository
from app.modules.participations.application.commands import (
    FairParticipantListResultDto,
    ListParticipantsByFairQuery,
)
from app.modules.participations.application.mappers import fair_row_to_list_item
from app.modules.participations.application.validators import ensure_fair_for_participation
from app.modules.participations.domain.exceptions import FairNotFoundForParticipationError
from app.modules.participations.domain.ports import ParticipationRepository

ALLOWED_SORT_FIELDS = frozenset(
    {
        "created_at",
        "updated_at",
        "hall",
        "stand",
        "company_name",
        "email",
        "phone",
        "country",
        "city",
        "notes",
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
        self._accept_visible_fair(query.organization_id, query.fair_id)

        page_params = normalize_page_params(query.page, query.page_size)
        sort_by = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
        sort_dir = normalize_sort_direction(query.sort_dir or DEFAULT_SORT_DIRECTION)

        result = self._participation_repository.list_by_fair(
            query.organization_id,
            query.fair_id,
            search=query.search,
            page=page_params.page,
            page_size=page_params.page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

        return FairParticipantListResultDto(
            items=[fair_row_to_list_item(row) for row in result.items],
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        )

    def _accept_visible_fair(self, organization_id: UUID, fair_id: UUID) -> None:
        try:
            ensure_fair_for_participation(self._fair_repository, organization_id, fair_id)
        except FairNotFoundForParticipationError:
            visible = self._fair_repository.get_visible(organization_id, fair_id)
            if visible is None or visible.origin != "system":
                raise

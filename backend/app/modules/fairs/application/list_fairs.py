from app.core.pagination import normalize_page_params, normalize_sort_direction
from app.modules.fairs.application.commands import FairListResultDto, ListFairsQuery
from app.modules.fairs.application.mappers import list_result_to_dto
from app.modules.fairs.domain.ports import FairRepository

ALLOWED_SORT_FIELDS = frozenset(
    {"created_at", "updated_at", "name", "start_date", "city", "country"}
)
DEFAULT_SORT_FIELD = "start_date"
DEFAULT_SORT_DIRECTION = "desc"


class ListFairsUseCase:
    def __init__(self, repository: FairRepository) -> None:
        self._repository = repository

    def execute(self, query: ListFairsQuery) -> FairListResultDto:
        page_params = normalize_page_params(query.page, query.page_size)
        sort_by = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
        sort_dir = normalize_sort_direction(query.sort_dir or DEFAULT_SORT_DIRECTION)

        result = self._repository.list_by_organization(
            query.organization_id,
            status=query.status,
            include_archived=query.include_archived,
            country=query.country,
            search=query.search,
            page=page_params.page,
            page_size=page_params.page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return list_result_to_dto(result)

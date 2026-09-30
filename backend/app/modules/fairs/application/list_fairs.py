from dataclasses import replace
from datetime import date

from app.core.pagination import normalize_page_params, normalize_sort_direction
from app.modules.fairs.application.commands import FairListResultDto, ListFairsQuery
from app.modules.fairs.application.mappers import list_result_to_dto
from app.modules.fairs.domain.ports import FairRepository
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)

ALLOWED_SORT_FIELDS = frozenset(
    {
        "created_at",
        "updated_at",
        "name",
        "start_date",
        "city",
        "country",
        "organizer",
        "venue",
        "status",
    }
)
DEFAULT_SORT_FIELD = "start_date"
DEFAULT_SORT_DIRECTION = "desc"


class ListFairsUseCase:
    def __init__(
        self,
        repository: FairRepository,
        run_history_repository: ScraperRunHistoryRepository,
    ) -> None:
        self._repository = repository
        self._run_history_repository = run_history_repository

    def execute(self, query: ListFairsQuery, *, today: date | None = None) -> FairListResultDto:
        page_params = normalize_page_params(query.page, query.page_size)
        sort_by = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
        sort_dir = normalize_sort_direction(query.sort_dir or DEFAULT_SORT_DIRECTION)

        result = self._repository.list_visible(
            query.organization_id,
            status=query.status,
            include_archived=query.include_archived,
            country=query.country,
            search=query.search,
            page=page_params.page,
            page_size=page_params.page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            default_date_order=query.default_date_order,
            today=today if today is not None else date.today(),
        )
        dto = list_result_to_dto(result)
        system_ids = [item.id for item in dto.items if item.origin == "system"]
        if not system_ids:
            return dto
        metadata = self._run_history_repository.list_latest_completed_system_runs(system_ids)
        items = []
        for item in dto.items:
            row = metadata.get(item.id)
            if row is None:
                items.append(item)
                continue
            items.append(
                replace(
                    item,
                    scraped_record_count=row.total_rows,
                    scraped_at=row.finished_at,
                )
            )
        return replace(dto, items=items)

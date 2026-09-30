from dataclasses import replace

from app.modules.fairs.application.commands import FairResult, GetFairQuery
from app.modules.fairs.application.mappers import fair_to_result
from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)


class GetFairUseCase:
    def __init__(
        self,
        repository: FairRepository,
        run_history_repository: ScraperRunHistoryRepository,
    ) -> None:
        self._repository = repository
        self._run_history_repository = run_history_repository

    def execute(self, query: GetFairQuery) -> FairResult:
        fair = self._repository.get_visible(query.organization_id, query.fair_id)
        if fair is None:
            raise FairNotFoundError("Fair not found")
        result = fair_to_result(fair)
        if fair.origin != "system":
            return result
        metadata = self._run_history_repository.list_latest_completed_system_runs([fair.id])
        row = metadata.get(fair.id)
        if row is None:
            return result
        return replace(
            result,
            scraped_record_count=row.total_rows,
            scraped_at=row.finished_at,
        )

"""Start a scraper run for a fair (Run v2 entry point)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.fairs.domain.exceptions import (
    FairNotFoundError,
    FairScraperAdapterNotConfiguredError,
    FairScraperUrlNotConfiguredError,
)
from app.modules.fairs.domain.ports import FairRepository
from app.modules.scraper.domain.scraper_run_history import ScraperRunHistory
from app.modules.scraper.domain.scraper_run_source import ScraperRunSource
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService


@dataclass(frozen=True)
class RunFairScraperCommand:
    organization_id: UUID
    fair_id: UUID


class RunFairScraperUseCase:
    def __init__(
        self,
        fair_repository: FairRepository,
        run_history_service: ScraperRunHistoryService,
    ) -> None:
        self._fair_repository = fair_repository
        self._run_history_service = run_history_service

    def execute(self, command: RunFairScraperCommand) -> ScraperRunHistory:
        fair = self._fair_repository.get_by_id(command.organization_id, command.fair_id)
        if fair is None:
            raise FairNotFoundError("Fair not found")

        adapter_key = (fair.adapter_key or "").strip()
        source_url = (fair.source_url or "").strip()
        if not adapter_key:
            raise FairScraperAdapterNotConfiguredError("Bu fuara bağlı scraper adapter bulunamadı.")
        if not source_url:
            raise FairScraperUrlNotConfiguredError("Bu fuar için scraper URL tanımlı değil.")

        fair_year = fair.start_date.year if fair.start_date is not None else None
        return self._run_history_service.start_run(
            adapter_key=adapter_key,
            input_url=source_url,
            fair_name=fair.name,
            fair_year=fair_year,
            organization_id=fair.organization_id,
            fair_id=fair.id,
            run_source=ScraperRunSource.FAIR_AUTOMATION,
        )

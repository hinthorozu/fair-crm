"""Start a customer contact enrichment run scoped to a fair's participants."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.fairs.domain.exceptions import FairEnrichmentNoCandidatesError, FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository
from app.modules.scraper.domain.enrichment_adapter import CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY
from app.modules.scraper.domain.scraper_run_history import ScraperRunHistory
from app.modules.scraper.domain.scraper_run_source import ScraperRunSource
from app.modules.scraper.services.enrichment_candidate_service import list_enrichment_candidates
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService


@dataclass(frozen=True)
class RunFairEnrichmentCommand:
    organization_id: UUID
    fair_id: UUID
    limit: int | None = None


class RunFairEnrichmentUseCase:
    def __init__(
        self,
        fair_repository: FairRepository,
        run_history_service: ScraperRunHistoryService,
        session: Session,
    ) -> None:
        self._fair_repository = fair_repository
        self._run_history_service = run_history_service
        self._session = session

    def execute(self, command: RunFairEnrichmentCommand) -> ScraperRunHistory:
        fair = self._fair_repository.get_by_id(command.organization_id, command.fair_id)
        if fair is None:
            raise FairNotFoundError("Fair not found")

        # Manual fair-scoped enrichment is a deliberate, single-fair re-check that the user
        # explicitly triggered. Prior enrichment scan state from other runs (pending_merge,
        # retry cooldowns, previously completed scans) must not silently block it — the user
        # should not need to know about or clear that bookkeeping themselves. Customers who
        # already have a real CRM email are still excluded (enforced inside the query itself).
        candidates = list_enrichment_candidates(
            self._session,
            command.organization_id,
            limit=command.limit,
            fair_id=fair.id,
            ignore_previous_scan_state=True,
        )
        if not candidates:
            raise FairEnrichmentNoCandidatesError(
                "Bu fuarda zenginleştirilecek müşteri bulunamadı."
            )

        fair_year = fair.start_date.year if fair.start_date is not None else None
        return self._run_history_service.start_run(
            adapter_key=CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY,
            input_url=None,
            fair_name=fair.name,
            fair_year=fair_year,
            organization_id=fair.organization_id,
            fair_id=fair.id,
            run_source=ScraperRunSource.ENRICHMENT,
        )

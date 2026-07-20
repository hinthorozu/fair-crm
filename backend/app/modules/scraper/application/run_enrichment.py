"""Start a customer contact enrichment run."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.scraper.domain.enrichment_adapter import (
    CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY,
    is_customer_contact_enrichment_adapter,
)
from app.modules.scraper.domain.scraper_run_history import ScraperRunHistory
from app.modules.scraper.domain.scraper_run_source import ScraperRunSource
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService


@dataclass(frozen=True)
class RunEnrichmentCommand:
    organization_id: UUID
    adapter_key: str
    limit: int | None = None
    fair_id: UUID | None = None
    fair_name: str | None = None
    fair_year: int | None = None


class EnrichmentAdapterNotSupportedError(ValueError):
    pass


class RunEnrichmentUseCase:
    def __init__(
        self,
        run_history_service: ScraperRunHistoryService,
        session: Session,
    ) -> None:
        self._run_history_service = run_history_service
        self._session = session

    def execute(self, command: RunEnrichmentCommand) -> ScraperRunHistory:
        normalized_key = command.adapter_key.strip().lower()
        if not is_customer_contact_enrichment_adapter(normalized_key):
            raise EnrichmentAdapterNotSupportedError(
                f"Enrichment run is only supported for {CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY}"
            )

        fair_name = command.fair_name or "Müşteri İletişim Zenginleştirme"
        return self._run_history_service.start_run(
            adapter_key=normalized_key,
            input_url=None,
            fair_name=fair_name,
            fair_year=command.fair_year,
            organization_id=command.organization_id,
            fair_id=command.fair_id,
            run_source=ScraperRunSource.ENRICHMENT,
        )

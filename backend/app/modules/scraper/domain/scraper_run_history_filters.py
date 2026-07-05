"""Filter parameters for scraper run history list queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.scraper.domain.scraper_run_history import ScraperRunStatus


@dataclass(frozen=True)
class ScraperRunHistoryListFilters:
    organization_id: UUID | None = None
    adapter_key: str | None = None
    adapter_id: UUID | None = None
    status: ScraperRunStatus | None = None
    engine_keys: tuple[str, ...] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    url_query: str | None = None
    fair_id: UUID | None = None

"""Load enrichment run summary stored in run log metadata."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.scraper.domain.scraper_run_log import ScraperRunLogLevel
from app.modules.scraper.services.scraper_run_log_service import ScraperRunLogService


def load_enrichment_summary_for_run(
    run_log_service: ScraperRunLogService,
    run_id: UUID,
) -> dict[str, Any] | None:
    logs = run_log_service.list_logs(run_id, limit=500)
    for log in reversed(logs):
        if log.level != ScraperRunLogLevel.SUCCESS:
            continue
        if log.step not in {"completed", "run_finished"}:
            continue
        metadata = log.metadata or {}
        if "customers_scanned" in metadata:
            return metadata
    return None

"""Load enrichment run summary stored in run log metadata."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.scraper.domain.scraper_run_log import ScraperRunLogLevel
from app.modules.scraper.services.scraper_run_log_service import ScraperRunLogService


_TERMINAL_SUMMARY_STEPS = ("completed", "run_finished")


def load_enrichment_summary_for_run(
    run_log_service: ScraperRunLogService,
    run_id: UUID,
) -> dict[str, Any] | None:
    """Load the terminal run-summary log for an enrichment run.

    Queries directly for the newest matching log entry rather than paging through
    logs oldest-first, so large runs (many candidates -> many log rows) don't cause
    the terminal summary entry to be missed once total log volume exceeds a page size.
    """
    log = run_log_service.find_latest_by_level_and_steps(
        run_id,
        level=ScraperRunLogLevel.SUCCESS,
        steps=_TERMINAL_SUMMARY_STEPS,
    )
    if log is None:
        return None
    metadata = log.metadata or {}
    return metadata if "customers_scanned" in metadata else None

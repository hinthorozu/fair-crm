"""Cooperative cancellation checks for long-running scraper jobs."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.scraper.domain.scraper_run_history import ACTIVE_SCRAPER_RUN_STATUSES, ScraperRunStatus
from app.modules.scraper.services.scraper_run_history_service import create_run_history_service
from app.modules.scraper.types.scraper_context import ScraperContext


class ScraperRunCancelledError(Exception):
    """Raised by adapters when a cooperative cancel/delete stop is observed mid-scrape."""


class RunCancelChecker:
    """Reads cancel state from a fresh DB session so API cancel requests are visible."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        run_id: UUID,
    ) -> None:
        self._session_factory = session_factory
        self._run_id = run_id

    def is_cancel_requested(self) -> bool:
        session = self._session_factory()
        try:
            run = create_run_history_service(session).get_run(self._run_id)
            # Missing history means the run was deleted (or never existed): treat as stop.
            if run is None:
                return True
            return run.status in {
                ScraperRunStatus.CANCEL_REQUESTED,
                ScraperRunStatus.CANCELLING,
                ScraperRunStatus.CANCELLED,
            }
        finally:
            session.close()

    def touch_heartbeat_if_active(self) -> None:
        """Keep last_heartbeat_at fresh so live workers are not treated as stale."""
        session = self._session_factory()
        try:
            service = create_run_history_service(session)
            run = service.get_run(self._run_id)
            if run is None or run.status not in ACTIVE_SCRAPER_RUN_STATUSES:
                return
            service.touch_heartbeat(self._run_id)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    def current_status(self) -> ScraperRunStatus | None:
        session = self._session_factory()
        try:
            run = create_run_history_service(session).get_run(self._run_id)
            return run.status if run is not None else None
        finally:
            session.close()


def ensure_run_not_cancelled(context: ScraperContext) -> None:
    """Adapter page-loop hook: stop cooperatively when cancel/delete is requested."""
    checker = context.options.get("cancel_checker")
    if not isinstance(checker, RunCancelChecker):
        return
    if checker.is_cancel_requested():
        raise ScraperRunCancelledError("Scraper run cancelled")
    checker.touch_heartbeat_if_active()

"""Cooperative cancellation checks for long-running scraper jobs."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.scraper.domain.scraper_run_history import ScraperRunStatus
from app.modules.scraper.services.scraper_run_history_service import create_run_history_service


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
            if run is None:
                return False
            return run.status in {
                ScraperRunStatus.CANCEL_REQUESTED,
                ScraperRunStatus.CANCELLING,
            }
        finally:
            session.close()

    def current_status(self) -> ScraperRunStatus | None:
        session = self._session_factory()
        try:
            run = create_run_history_service(session).get_run(self._run_id)
            return run.status if run is not None else None
        finally:
            session.close()

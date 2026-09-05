"""Cooperative cancellation checks for long-running scraper jobs."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.modules.scraper.domain.scraper_run_history import ACTIVE_SCRAPER_RUN_STATUSES, ScraperRunStatus
from app.modules.scraper.services.scraper_run_history_service import create_run_history_service
from app.modules.scraper.types.scraper_context import ScraperContext
from app.shared.running_work_lifecycle import (
    RunningWorkLifecycleCancelledError,
    RunningWorkLifecycleCheckpoint,
)


class ScraperRunCancelledError(Exception):
    """Raised by adapters when a cooperative cancel/delete stop is observed mid-scrape."""


class RunCancelChecker:
    """Read local cancel state plus Core lifecycle state from fresh sources.

    Production runners use ``SessionLocal`` and therefore enable the OL07-05
    lifecycle checkpoint by default.  Injected test/session factories retain the
    historical local-only behavior unless lifecycle enforcement is requested
    explicitly, keeping the session-factory test seam deterministic.
    """

    def __init__(
        self,
        session_factory: Callable[[], Session],
        run_id: UUID,
        *,
        organization_id: UUID | None = None,
        enforce_lifecycle: bool | None = None,
        lifecycle_checkpoint: RunningWorkLifecycleCheckpoint | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._run_id = run_id
        self._organization_id = organization_id
        if enforce_lifecycle is None:
            enforce_lifecycle = session_factory is SessionLocal
        self._lifecycle_checkpoint = lifecycle_checkpoint
        if (
            self._lifecycle_checkpoint is None
            and enforce_lifecycle
            and organization_id is not None
        ):
            self._lifecycle_checkpoint = RunningWorkLifecycleCheckpoint(organization_id)

    def is_cancel_requested(self) -> bool:
        session = self._session_factory()
        try:
            run = create_run_history_service(session).get_run(
                self._run_id,
                organization_id=self._organization_id,
            )
            # Missing history (including foreign-organization scope) means stop.
            if run is None:
                return True
            if run.status in {
                ScraperRunStatus.CANCEL_REQUESTED,
                ScraperRunStatus.CANCELLING,
                ScraperRunStatus.CANCELLED,
            }:
                return True
        finally:
            session.close()

        if self._lifecycle_checkpoint is not None:
            try:
                self._lifecycle_checkpoint.check()
            except RunningWorkLifecycleCancelledError:
                return True
            # OrganizationLifecycleUnavailableError intentionally propagates:
            # the runner fails closed instead of labelling an authority outage as
            # an explicit suspension cancellation.
        return False

    def touch_heartbeat_if_active(self) -> None:
        """Keep last_heartbeat_at fresh so live workers are not treated as stale."""
        session = self._session_factory()
        try:
            service = create_run_history_service(session)
            run = service.get_run(
                self._run_id,
                organization_id=self._organization_id,
            )
            if run is None or run.status not in ACTIVE_SCRAPER_RUN_STATUSES:
                return
            service.touch_heartbeat(
                self._run_id,
                organization_id=self._organization_id,
            )
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    def current_status(self) -> ScraperRunStatus | None:
        session = self._session_factory()
        try:
            run = create_run_history_service(session).get_run(
                self._run_id,
                organization_id=self._organization_id,
            )
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

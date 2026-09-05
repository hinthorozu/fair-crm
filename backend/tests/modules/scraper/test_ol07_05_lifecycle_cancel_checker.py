from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.kyrox_core.lifecycle import OrganizationLifecycleUnavailableError
from app.modules.scraper.domain.scraper_run_history import ScraperRunStatus
from app.modules.scraper.services import scraper_run_cancellation as cancellation_module
from app.modules.scraper.services.scraper_run_cancellation import RunCancelChecker
from app.shared.running_work_lifecycle import RunningWorkLifecycleCancelledError


class _Session:
    def close(self) -> None:
        pass


class _HistoryService:
    def __init__(self, status: ScraperRunStatus) -> None:
        self._status = status

    def get_run(self, run_id, organization_id=None):
        return SimpleNamespace(status=self._status)


class _Checkpoint:
    def __init__(self, exc: Exception | None = None) -> None:
        self._exc = exc
        self.calls = 0

    def check(self) -> None:
        self.calls += 1
        if self._exc is not None:
            raise self._exc


def test_scraper_checker_maps_explicit_lifecycle_stop_to_cooperative_cancel(monkeypatch):
    organization_id = uuid4()
    checkpoint = _Checkpoint(
        RunningWorkLifecycleCancelledError(
            organization_id=organization_id,
            status="suspended",
        )
    )
    monkeypatch.setattr(
        cancellation_module,
        "create_run_history_service",
        lambda _session: _HistoryService(ScraperRunStatus.RUNNING),
    )
    checker = RunCancelChecker(
        lambda: _Session(),  # type: ignore[arg-type]
        uuid4(),
        organization_id=organization_id,
        enforce_lifecycle=True,
        lifecycle_checkpoint=checkpoint,  # type: ignore[arg-type]
    )

    assert checker.is_cancel_requested() is True
    assert checkpoint.calls == 1


def test_scraper_checker_propagates_lifecycle_authority_outage(monkeypatch):
    organization_id = uuid4()
    checkpoint = _Checkpoint(OrganizationLifecycleUnavailableError("authority unavailable"))
    monkeypatch.setattr(
        cancellation_module,
        "create_run_history_service",
        lambda _session: _HistoryService(ScraperRunStatus.RUNNING),
    )
    checker = RunCancelChecker(
        lambda: _Session(),  # type: ignore[arg-type]
        uuid4(),
        organization_id=organization_id,
        enforce_lifecycle=True,
        lifecycle_checkpoint=checkpoint,  # type: ignore[arg-type]
    )

    with pytest.raises(OrganizationLifecycleUnavailableError):
        checker.is_cancel_requested()

    assert checkpoint.calls == 1

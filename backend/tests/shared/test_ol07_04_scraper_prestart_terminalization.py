from types import SimpleNamespace
from uuid import uuid4

import app.shared.queued_work_lifecycle as lifecycle
from app.modules.scraper.domain.scraper_run_history import ScraperRunStatus


class _Session:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def _descriptor(organization_id, run_id, operation_id, operation_run_id):
    return lifecycle._QueuedWorkDescriptor(
        module="app.modules.scraper.application.fair_scraper_job_runner",
        function="run_fair_scraper",
        command=SimpleNamespace(
            run_id=run_id,
            operation_id=operation_id,
            operation_run_id=operation_run_id,
        ),
        organization_id=organization_id,
    )


def test_scraper_prestart_cancellation_syncs_only_still_running_run(monkeypatch):
    organization_id = uuid4()
    run_id = uuid4()
    operation_id = uuid4()
    operation_run_id = uuid4()
    session = _Session()
    cancelled = SimpleNamespace(id=run_id, status=ScraperRunStatus.CANCELLED)
    calls = []

    class History:
        def cancel_run(self, requested_run_id, *, reason, organization_id):
            calls.append((requested_run_id, reason, organization_id))
            return cancelled

    synced = []
    monkeypatch.setattr(lifecycle, "SessionLocal", lambda: session)
    monkeypatch.setattr(lifecycle, "create_run_history_service", lambda db: History())
    monkeypatch.setattr(
        lifecycle,
        "sync_operation_run_from_scraper",
        lambda db, **kwargs: synced.append(kwargs),
    )
    reason = "organization_lifecycle_prestart_cancelled:suspended"

    lifecycle._terminalize_scraper(
        _descriptor(organization_id, run_id, operation_id, operation_run_id),
        reason=reason,
    )

    assert calls == [(run_id, reason, organization_id)]
    assert len(synced) == 1
    assert synced[0]["organization_id"] == organization_id
    assert synced[0]["operation_id"] == operation_id
    assert synced[0]["operation_run_id"] == operation_run_id
    assert synced[0]["scraper_run"] is cancelled
    assert session.commits == 1
    assert session.rollbacks == 0
    assert session.closed is True


def test_scraper_prestart_cancellation_does_not_rewrite_completed_race(monkeypatch):
    organization_id = uuid4()
    run_id = uuid4()
    session = _Session()
    completed = SimpleNamespace(id=run_id, status=ScraperRunStatus.COMPLETED)

    class History:
        def cancel_run(self, requested_run_id, *, reason, organization_id):
            assert requested_run_id == run_id
            return completed

    monkeypatch.setattr(lifecycle, "SessionLocal", lambda: session)
    monkeypatch.setattr(lifecycle, "create_run_history_service", lambda db: History())
    monkeypatch.setattr(
        lifecycle,
        "sync_operation_run_from_scraper",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("completed scraper run must not be resynchronized as cancelled")
        ),
    )

    lifecycle._terminalize_scraper(
        _descriptor(organization_id, run_id, uuid4(), uuid4()),
        reason="organization_lifecycle_prestart_cancelled:suspended",
    )

    assert completed.status == ScraperRunStatus.COMPLETED
    assert session.commits == 0
    assert session.rollbacks == 0
    assert session.closed is True

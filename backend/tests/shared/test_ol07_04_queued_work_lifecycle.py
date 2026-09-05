from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import app.shared.queued_work_lifecycle as lifecycle
from app.modules.data_integration.domain.entities import ImportJob
from app.modules.imports.domain.entities import ImportBatch
from app.modules.imports.domain.value_objects import (
    ImportBatchStatus,
    ImportJobStatus,
    ImportSourceType,
)


def _registered_import_function():
    return None


_registered_import_function.__module__ = lifecycle._IMPORT_MODULE
_registered_import_function.__name__ = "run_analyze"


def _command(organization_id):
    return SimpleNamespace(organization_id=organization_id, job_id=uuid4())


def test_suspended_queued_work_is_terminalized_before_start(monkeypatch):
    organization_id = uuid4()
    command = _command(organization_id)
    terminalized = []

    monkeypatch.setattr(lifecycle, "_is_locally_startable", lambda descriptor: True)
    monkeypatch.setattr(
        lifecycle,
        "OrganizationLifecycleGuard",
        lambda: SimpleNamespace(
            get_snapshot=lambda requested_id: SimpleNamespace(
                organization_id=requested_id,
                status="suspended",
                work_allowed=False,
            )
        ),
    )
    monkeypatch.setattr(
        lifecycle,
        "_terminalize",
        lambda descriptor, *, reason: terminalized.append((descriptor, reason)),
    )

    allowed = lifecycle.should_execute_queued_product_work(
        _registered_import_function,
        (command,),
        {},
    )

    assert allowed is False
    assert len(terminalized) == 1
    descriptor, reason = terminalized[0]
    assert descriptor.organization_id == organization_id
    assert descriptor.command is command
    assert reason == "organization_lifecycle_prestart_cancelled:suspended"


def test_active_queued_work_starts_without_terminalization(monkeypatch):
    organization_id = uuid4()
    command = _command(organization_id)
    terminalized = []

    monkeypatch.setattr(lifecycle, "_is_locally_startable", lambda descriptor: True)
    monkeypatch.setattr(
        lifecycle,
        "OrganizationLifecycleGuard",
        lambda: SimpleNamespace(
            get_snapshot=lambda requested_id: SimpleNamespace(
                organization_id=requested_id,
                status="active",
                work_allowed=True,
            )
        ),
    )
    monkeypatch.setattr(
        lifecycle,
        "_terminalize",
        lambda descriptor, *, reason: terminalized.append((descriptor, reason)),
    )

    assert lifecycle.should_execute_queued_product_work(
        _registered_import_function,
        (command,),
        {},
    ) is True
    assert terminalized == []


def test_lifecycle_unavailable_fails_closed_without_terminalizing(monkeypatch):
    organization_id = uuid4()
    command = _command(organization_id)
    terminalized = []

    class UnavailableGuard:
        def get_snapshot(self, requested_id):
            assert requested_id == organization_id
            raise lifecycle.OrganizationLifecycleUnavailableError("unavailable")

    monkeypatch.setattr(lifecycle, "_is_locally_startable", lambda descriptor: True)
    monkeypatch.setattr(lifecycle, "OrganizationLifecycleGuard", UnavailableGuard)
    monkeypatch.setattr(
        lifecycle,
        "_terminalize",
        lambda descriptor, *, reason: terminalized.append((descriptor, reason)),
    )

    assert lifecycle.should_execute_queued_product_work(
        _registered_import_function,
        (command,),
        {},
    ) is False
    assert terminalized == []


def test_decision_keeps_organization_scope(monkeypatch):
    active_org = uuid4()
    suspended_org = uuid4()
    terminalized_orgs = []

    class ScopedGuard:
        def get_snapshot(self, requested_id):
            return SimpleNamespace(
                organization_id=requested_id,
                status="active" if requested_id == active_org else "suspended",
                work_allowed=requested_id == active_org,
            )

    monkeypatch.setattr(lifecycle, "_is_locally_startable", lambda descriptor: True)
    monkeypatch.setattr(lifecycle, "OrganizationLifecycleGuard", ScopedGuard)
    monkeypatch.setattr(
        lifecycle,
        "_terminalize",
        lambda descriptor, *, reason: terminalized_orgs.append(descriptor.organization_id),
    )

    assert lifecycle.should_execute_queued_product_work(
        _registered_import_function,
        (_command(active_org),),
        {},
    ) is True
    assert lifecycle.should_execute_queued_product_work(
        _registered_import_function,
        (_command(suspended_org),),
        {},
    ) is False
    assert terminalized_orgs == [suspended_org]


def test_prestart_cancelled_apply_terminalizes_batch_that_was_marked_applying(monkeypatch):
    organization_id = uuid4()
    stamp = datetime.now(tz=UTC)
    batch = ImportBatch.create_from_canonical(
        organization_id=organization_id,
        fair_id=None,
        source_type=ImportSourceType.SCRAPER,
        file_name="ol07-04.json",
        total_rows=1,
        valid_rows=1,
        invalid_rows=0,
        raw_preview_json={},
        now=stamp,
    )
    batch.mark_applying(now=stamp)
    job = ImportJob.create_apply_job(
        organization_id=organization_id,
        batch_id=batch.id,
        progress_total=1,
        now=stamp,
    )
    session = SimpleNamespace(
        commits=0,
        rollbacks=0,
        closed=False,
    )
    session.commit = lambda: setattr(session, "commits", session.commits + 1)
    session.rollback = lambda: setattr(session, "rollbacks", session.rollbacks + 1)
    session.close = lambda: setattr(session, "closed", True)

    class JobRepository:
        def __init__(self, db):
            assert db is session

        def get_by_id(self, requested_organization_id, requested_job_id):
            assert requested_organization_id == organization_id
            assert requested_job_id == job.id
            return job

        def update(self, updated):
            assert updated is job
            return updated

    class BatchRepository:
        def __init__(self, db):
            assert db is session

        def get_by_id(self, requested_organization_id, requested_batch_id):
            assert requested_organization_id == organization_id
            assert requested_batch_id == batch.id
            return batch

        def update(self, updated):
            assert updated is batch
            return updated

    monkeypatch.setattr(lifecycle, "SessionLocal", lambda: session)
    monkeypatch.setattr(lifecycle, "SqlAlchemyImportJobRepository", JobRepository)
    monkeypatch.setattr(lifecycle, "SqlAlchemyImportBatchRepository", BatchRepository)
    reason = "organization_lifecycle_prestart_cancelled:suspended"
    descriptor = lifecycle._QueuedWorkDescriptor(
        module=lifecycle._IMPORT_MODULE,
        function="run_apply",
        command=SimpleNamespace(job_id=job.id),
        organization_id=organization_id,
    )

    lifecycle._terminalize_import(descriptor, reason=reason)

    assert job.status == ImportJobStatus.CANCELLED
    assert batch.status == ImportBatchStatus.CANCELLED
    assert batch.notes == reason
    assert batch.completed_at is not None
    assert session.commits == 1
    assert session.rollbacks == 0
    assert session.closed is True

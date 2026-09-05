from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.modules.mail_send_operations.application.process_mail_send_operations_worker as worker_module
from app.modules.mail_send_operations.application.process_mail_send_operations_worker import (
    ProcessMailSendOperationsWorker,
)
from app.modules.mail_send_operations.domain.value_objects import (
    MailSendOperationStatus,
    MailSendSourceType,
)


class _Repository:
    def __init__(self, records):
        self.records = {(record.organization_id, record.id): record for record in records}

    def get_by_id(self, organization_id, operation_id):
        return self.records.get((organization_id, operation_id))

    def list_queued_for_worker(self, *, max_batch_size, now):
        return list(self.records.values())[:max_batch_size]


class _MailService:
    def __init__(self):
        self.cancelled = []

    def mark_cancelled(self, organization_id, operation_id, *, message=None):
        self.cancelled.append((organization_id, operation_id, message))


class _FairBulkHandler:
    def __init__(self):
        self.failed = []

    def get_outbox_for_operation(self, organization_id, operation_id):
        return None

    def sync_outbox_failed(self, organization_id, batch_id, outbox_id, *, message):
        self.failed.append((organization_id, batch_id, outbox_id, message))


class _Session:
    def __init__(self):
        self.commits = 0
        self.flushes = 0

    def commit(self):
        self.commits += 1

    def flush(self):
        self.flushes += 1


def _candidate(organization_id, *, source_type=MailSendSourceType.MANUAL_EMAIL):
    return SimpleNamespace(
        id=uuid4(),
        organization_id=organization_id,
        status=MailSendOperationStatus.QUEUED,
        source_type=source_type,
    )


def _worker(*records):
    worker = object.__new__(ProcessMailSendOperationsWorker)
    worker._repository = _Repository(records)
    worker._mail_service = _MailService()
    worker._fair_bulk_handler = _FairBulkHandler()
    return worker


def test_suspended_mail_is_cancelled_before_claim(monkeypatch):
    organization_id = uuid4()
    candidate = _candidate(organization_id)
    worker = _worker(candidate)

    monkeypatch.setattr(
        worker_module,
        "OrganizationLifecycleGuard",
        lambda: SimpleNamespace(
            get_snapshot=lambda requested_id: SimpleNamespace(
                organization_id=requested_id,
                status="suspended",
                work_allowed=False,
            )
        ),
    )

    assert worker._lifecycle_allows_candidate_start(candidate) is False
    assert worker._mail_service.cancelled == [
        (
            organization_id,
            candidate.id,
            "organization_lifecycle_prestart_cancelled:suspended",
        )
    ]


def test_mail_gate_is_organization_scoped(monkeypatch):
    active_org = uuid4()
    suspended_org = uuid4()
    active = _candidate(active_org)
    suspended = _candidate(suspended_org)
    worker = _worker(active, suspended)

    class ScopedGuard:
        def get_snapshot(self, requested_id):
            is_active = requested_id == active_org
            return SimpleNamespace(
                organization_id=requested_id,
                status="active" if is_active else "suspended",
                work_allowed=is_active,
            )

    monkeypatch.setattr(worker_module, "OrganizationLifecycleGuard", ScopedGuard)

    assert worker._lifecycle_allows_candidate_start(active) is True
    assert worker._lifecycle_allows_candidate_start(suspended) is False
    assert [item[0] for item in worker._mail_service.cancelled] == [suspended_org]


def test_lifecycle_unavailable_defers_mail_without_cancelling(monkeypatch):
    organization_id = uuid4()
    candidate = _candidate(organization_id)
    worker = _worker(candidate)

    class UnavailableGuard:
        def get_snapshot(self, requested_id):
            assert requested_id == organization_id
            raise worker_module.OrganizationLifecycleUnavailableError("unavailable")

    monkeypatch.setattr(worker_module, "OrganizationLifecycleGuard", UnavailableGuard)

    assert worker._lifecycle_allows_candidate_start(candidate) is False
    assert worker._mail_service.cancelled == []


def test_lifecycle_deferred_candidate_is_not_counted_as_picked(monkeypatch):
    organization_id = uuid4()
    candidate = _candidate(organization_id)
    worker = _worker(candidate)
    session = _Session()
    worker._session = session

    monkeypatch.setattr(
        worker_module,
        "get_settings",
        lambda: SimpleNamespace(
            mail_sending_timeout_minutes=10,
            mail_worker_max_batch_size=10,
        ),
    )
    monkeypatch.setattr(worker, "_recover_stuck_sending", lambda **kwargs: 0)
    monkeypatch.setattr(worker, "_sync_fair_batch_progress", lambda records: None)
    monkeypatch.setattr(worker, "_lifecycle_allows_candidate_start", lambda record: False)
    monkeypatch.setattr(
        worker,
        "_process_candidate",
        lambda *args, **kwargs: pytest.fail("deferred mail must not be processed"),
    )

    result = worker.run()

    assert result.picked_count == 0
    assert result.skipped_count == 1
    assert result.sent_count == 0
    assert result.failed_count == 0
    assert session.commits == 1
    assert session.flushes == 1

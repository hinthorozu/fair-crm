from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleUnavailableError,
    OrganizationWorkNotAllowedError,
)
from app.modules.mail_send_operations.application.mail_send_operation_service import (
    MailSendOperationService,
)
from app.modules.mail_send_operations.application.process_mail_send_operations_worker import (
    ProcessMailSendOperationsWorker,
)
from app.modules.mail_send_operations.domain.value_objects import (
    MailSendOperationStatus,
    MailSendSourceType,
)
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
    SqlAlchemyMailSendOperationRepository,
)


class _Repository:
    def __init__(self, claimed):
        self.claimed = claimed
        self.auto_retry = []

    def try_claim_queued_operation(self, organization_id, operation_id, *, now):
        assert organization_id == self.claimed.organization_id
        assert operation_id == self.claimed.id
        return self.claimed

    def set_auto_retry_pending(self, organization_id, operation_id, *, enabled):
        self.auto_retry.append((organization_id, operation_id, enabled))


class _MailService:
    def __init__(self):
        self.cancelled = []
        self.failed = []
        self.sending = []

    def mark_worker_sending(self, organization_id, operation_id):
        self.sending.append((organization_id, operation_id))

    def mark_cancelled(self, organization_id, operation_id, *, message=None):
        self.cancelled.append((organization_id, operation_id, message))

    def mark_failed(
        self,
        organization_id,
        operation_id,
        *,
        error_code,
        error_message,
        provider_status=None,
    ):
        self.failed.append(
            (organization_id, operation_id, error_code, error_message, provider_status)
        )


class _Dispatcher:
    def __init__(self, exc):
        self.exc = exc
        self.calls = []

    def dispatch(self, operation):
        self.calls.append(operation)
        raise self.exc


def _claimed_operation():
    return SimpleNamespace(
        id=uuid4(),
        organization_id=uuid4(),
        source_type=MailSendSourceType.MANUAL_EMAIL,
        status=MailSendOperationStatus.SENDING,
    )


def _worker_for(claimed, exc):
    worker = object.__new__(ProcessMailSendOperationsWorker)
    worker._repository = _Repository(claimed)
    worker._mail_service = _MailService()
    worker._dispatcher = _Dispatcher(exc)
    return worker


def test_suspend_after_claim_cancels_before_provider_handoff_terminalization():
    claimed = _claimed_operation()
    worker = _worker_for(
        claimed,
        OrganizationWorkNotAllowedError(
            "Organization lifecycle does not allow product work: suspended"
        ),
    )

    outcome = worker._process_candidate(claimed, now=datetime.now(tz=UTC))

    assert outcome == "cancelled"
    assert worker._mail_service.failed == []
    assert worker._repository.auto_retry == []
    assert len(worker._mail_service.cancelled) == 1
    organization_id, operation_id, message = worker._mail_service.cancelled[0]
    assert organization_id == claimed.organization_id
    assert operation_id == claimed.id
    assert message.startswith("organization_lifecycle_provider_dispatch_cancelled:")


def test_lifecycle_unavailable_after_claim_fails_closed_without_false_cancellation():
    claimed = _claimed_operation()
    worker = _worker_for(
        claimed,
        OrganizationLifecycleUnavailableError("Organization lifecycle authority unavailable"),
    )

    outcome = worker._process_candidate(claimed, now=datetime.now(tz=UTC))

    assert outcome == "failed"
    assert worker._mail_service.cancelled == []
    assert worker._repository.auto_retry == [
        (claimed.organization_id, claimed.id, True),
    ]
    assert worker._mail_service.failed == [
        (
            claimed.organization_id,
            claimed.id,
            "OrganizationLifecycleUnavailableError",
            "Organization lifecycle authority unavailable",
            None,
        )
    ]


def test_synchronous_send_records_explicit_suspend_as_cancelled(db_session, organization_id):
    repository = SqlAlchemyMailSendOperationRepository(db_session)
    service = MailSendOperationService(repository)
    params = CreateMailSendOperationParams(
        organization_id=organization_id,
        source_type=MailSendSourceType.SMTP_TEST,
        recipient_email="blocked@example.com",
        subject="Blocked",
    )

    def _blocked_send():
        raise OrganizationWorkNotAllowedError(
            "Organization lifecycle does not allow product work: suspended"
        )

    with pytest.raises(OrganizationWorkNotAllowedError):
        service.execute_synchronous_send(params, send_fn=_blocked_send)

    records = repository.list_by_organization(organization_id)
    assert len(records) == 1
    record = records[0]
    assert record.status == MailSendOperationStatus.CANCELLED
    assert record.cancelled_at is not None
    assert record.failed_at is None
    assert [entry["event"] for entry in record.operation_logs] == [
        "queued",
        "sending_started",
        "cancelled",
    ]
    assert record.error_message.startswith(
        "organization_lifecycle_provider_dispatch_cancelled:"
    )


def test_synchronous_send_lifecycle_unavailable_is_not_recorded_as_cancelled(
    db_session,
    organization_id,
):
    repository = SqlAlchemyMailSendOperationRepository(db_session)
    service = MailSendOperationService(repository)
    params = CreateMailSendOperationParams(
        organization_id=organization_id,
        source_type=MailSendSourceType.SMTP_TEST,
        recipient_email="deferred@example.com",
        subject="Deferred",
    )

    def _unavailable_send():
        raise OrganizationLifecycleUnavailableError("Organization lifecycle authority unavailable")

    with pytest.raises(OrganizationLifecycleUnavailableError):
        service.execute_synchronous_send(params, send_fn=_unavailable_send)

    records = repository.list_by_organization(organization_id)
    assert len(records) == 1
    record = records[0]
    assert record.status == MailSendOperationStatus.FAILED
    assert record.cancelled_at is None
    assert record.error_code == "OrganizationLifecycleUnavailableError"
    assert [entry["event"] for entry in record.operation_logs] == [
        "queued",
        "sending_started",
        "failed",
    ]

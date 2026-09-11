"""OL08-02 certification that closure reuses the existing OL-07 quiescence guards.

This file intentionally changes no production behavior.  It composes an actual
OL08-01 closure execution with the already-shipped OL-07 queued/running/provider
boundaries and terminal mail semantics so later OL08 export planning cannot
silently weaken suspension behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.modules.email_delivery.application.email_delivery_service as delivery_module
import app.shared.queued_work_lifecycle as queued_lifecycle
from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleUnavailableError,
    OrganizationWorkNotAllowedError,
)
from app.integrations.kyrox_core.ports import AuthContext
from app.modules.email_delivery.application.email_delivery_service import EmailDeliveryService
from app.modules.email_delivery.domain.exceptions import PROVIDER_HANDOFF_UNCERTAIN_ERROR_CODE
from app.modules.mail_send_operations.application.mail_send_operation_service import (
    MailSendOperationService,
)
from app.modules.mail_send_operations.domain.value_objects import (
    MailSendOperationStatus,
    MailSendSourceType,
)
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
    SqlAlchemyMailSendOperationRepository,
)
from app.modules.organization_closure.application.service import OrganizationClosureService
from app.modules.organization_closure.infrastructure.repository import (
    SqlAlchemyOrganizationClosureRepository,
)
from app.shared.running_work_lifecycle import (
    RunningWorkLifecycleCancelledError,
    RunningWorkLifecycleCheckpoint,
)


class _Authorization:
    def check_permission(self, **kwargs) -> bool:
        return True


class _SuspendedLifecycle:
    def get_snapshot(self, organization_id):
        return SimpleNamespace(
            organization_id=organization_id,
            status="suspended",
            work_allowed=False,
            is_deleted=False,
        )


class _Audit:
    def record_event(self, **kwargs) -> None:
        return None


def _auth(organization_id):
    return AuthContext(
        user_id=uuid4(),
        email="platform-admin@example.com",
        session_id=uuid4(),
        organization_id=organization_id,
    )


def _start_closure(db_session, organization_id):
    service = OrganizationClosureService(
        SqlAlchemyOrganizationClosureRepository(db_session),
        _Authorization(),  # type: ignore[arg-type]
        _SuspendedLifecycle(),  # type: ignore[arg-type]
        _Audit(),  # type: ignore[arg-type]
    )
    execution = service.start(
        organization_id=organization_id,
        idempotency_key=f"ol08-02-{uuid4()}",
        auth=_auth(organization_id),
        access_token="system-token",
    )
    db_session.flush()
    return execution


def _registered_import_function():
    return None


_registered_import_function.__module__ = queued_lifecycle._IMPORT_MODULE
_registered_import_function.__name__ = "run_analyze"


def _mail_params(organization_id, *, subject: str) -> CreateMailSendOperationParams:
    return CreateMailSendOperationParams(
        organization_id=organization_id,
        source_type=MailSendSourceType.MANUAL_EMAIL,
        recipient_email="ol08-quiescence@example.com",
        subject=subject,
        body_text="OL08-02 quiescence certification",
    )


def test_closure_execution_does_not_bypass_queued_prestart_cancellation(
    monkeypatch,
    db_session,
    organization_id,
):
    execution = _start_closure(db_session, organization_id)
    terminalized = []

    monkeypatch.setattr(queued_lifecycle, "_is_locally_startable", lambda descriptor: True)
    monkeypatch.setattr(
        queued_lifecycle,
        "OrganizationLifecycleGuard",
        lambda: _SuspendedLifecycle(),
    )
    monkeypatch.setattr(
        queued_lifecycle,
        "_terminalize",
        lambda descriptor, *, reason: terminalized.append((descriptor, reason)),
    )

    command = SimpleNamespace(organization_id=organization_id, job_id=uuid4())
    allowed = queued_lifecycle.should_execute_queued_product_work(
        _registered_import_function,
        (command,),
        {},
    )

    assert execution.organization_id == organization_id
    assert allowed is False
    assert len(terminalized) == 1
    descriptor, reason = terminalized[0]
    assert descriptor.organization_id == execution.organization_id
    assert reason == "organization_lifecycle_prestart_cancelled:suspended"


def test_closure_execution_does_not_bypass_running_safe_checkpoint(
    db_session,
    organization_id,
):
    execution = _start_closure(db_session, organization_id)

    with pytest.raises(RunningWorkLifecycleCancelledError) as exc_info:
        RunningWorkLifecycleCheckpoint(
            organization_id,
            guard=_SuspendedLifecycle(),  # type: ignore[arg-type]
        ).check()

    assert execution.organization_id == organization_id
    assert exc_info.value.organization_id == organization_id
    assert exc_info.value.status == "suspended"


def test_closure_execution_does_not_bypass_final_provider_handoff_guard(
    monkeypatch,
    db_session,
    organization_id,
):
    execution = _start_closure(db_session, organization_id)
    provider_calls = []

    class _ProviderLifecycle:
        def require_work_allowed(self, requested_organization_id):
            assert requested_organization_id == organization_id
            raise OrganizationWorkNotAllowedError(
                "Organization lifecycle does not allow product work: suspended"
            )

    service = EmailDeliveryService(
        db_session,
        lifecycle_guard=_ProviderLifecycle(),  # type: ignore[arg-type]
    )
    monkeypatch.setattr(
        service,
        "_resolve_account",
        lambda requested_organization_id, email_account_id: (object(), None, None),
    )
    monkeypatch.setattr(
        delivery_module,
        "deliver_with_dispatcher",
        lambda *args, **kwargs: provider_calls.append((args, kwargs)),
    )

    with pytest.raises(OrganizationWorkNotAllowedError):
        service.send(
            organization_id=organization_id,
            email_account_id=uuid4(),
            to="blocked@example.com",
            subject="must not hand off",
            body_text="blocked while closure is open",
        )

    assert execution.organization_id == organization_id
    assert provider_calls == []


def test_lifecycle_authority_outage_still_fails_closed_after_closure_start(
    monkeypatch,
    db_session,
    organization_id,
):
    _start_closure(db_session, organization_id)
    terminalized = []

    class _UnavailableLifecycle:
        def get_snapshot(self, requested_organization_id):
            assert requested_organization_id == organization_id
            raise OrganizationLifecycleUnavailableError("Core lifecycle unavailable")

    monkeypatch.setattr(queued_lifecycle, "_is_locally_startable", lambda descriptor: True)
    monkeypatch.setattr(queued_lifecycle, "OrganizationLifecycleGuard", _UnavailableLifecycle)
    monkeypatch.setattr(
        queued_lifecycle,
        "_terminalize",
        lambda descriptor, *, reason: terminalized.append((descriptor, reason)),
    )

    command = SimpleNamespace(organization_id=organization_id, job_id=uuid4())
    assert queued_lifecycle.should_execute_queued_product_work(
        _registered_import_function,
        (command,),
        {},
    ) is False
    assert terminalized == []

    with pytest.raises(OrganizationLifecycleUnavailableError):
        RunningWorkLifecycleCheckpoint(
            organization_id,
            guard=_UnavailableLifecycle(),  # type: ignore[arg-type]
        ).check()


def test_suspension_cancelled_mail_is_not_resurrected_by_closure_execution(
    db_session,
    organization_id,
):
    repository = SqlAlchemyMailSendOperationRepository(db_session)
    service = MailSendOperationService(repository)
    cancelled = service.create_mail_send_operation(
        _mail_params(organization_id, subject="cancelled-before-closure"),
        check_consent=False,
    )
    service.mark_cancelled(
        organization_id,
        cancelled.id,
        message="organization_lifecycle_prestart_cancelled:suspended",
    )
    db_session.commit()

    _start_closure(db_session, organization_id)
    db_session.commit()

    ready = repository.list_queued_for_worker(
        max_batch_size=10,
        now=datetime.now(tz=UTC) + timedelta(seconds=1),
    )
    retryable = repository.list_failed_for_auto_retry(
        max_batch_size=10,
        now=datetime.now(tz=UTC) + timedelta(seconds=1),
    )
    persisted = repository.get_by_id(organization_id, cancelled.id)

    assert persisted is not None
    assert persisted.status == MailSendOperationStatus.CANCELLED
    assert cancelled.id not in {record.id for record in ready}
    assert cancelled.id not in {record.id for record in retryable}


def test_ambiguous_inflight_handoff_remains_terminal_non_auto_retry_during_closure(
    db_session,
    organization_id,
):
    repository = SqlAlchemyMailSendOperationRepository(db_session)
    service = MailSendOperationService(repository)
    operation = service.create_mail_send_operation(
        _mail_params(organization_id, subject="uncertain-before-closure"),
        check_consent=False,
    )
    service.mark_failed(
        organization_id,
        operation.id,
        error_code=PROVIDER_HANDOFF_UNCERTAIN_ERROR_CODE,
        error_message="provider acceptance unknown",
    )
    db_session.commit()

    _start_closure(db_session, organization_id)
    db_session.commit()

    persisted = repository.get_by_id(organization_id, operation.id)
    retryable = repository.list_failed_for_auto_retry(
        max_batch_size=10,
        now=datetime.now(tz=UTC) + timedelta(seconds=1),
    )

    assert persisted is not None
    assert persisted.status == MailSendOperationStatus.FAILED
    assert persisted.error_code == PROVIDER_HANDOFF_UNCERTAIN_ERROR_CODE
    assert persisted.metadata_json["auto_retry_pending"] is False
    assert operation.id not in {record.id for record in retryable}

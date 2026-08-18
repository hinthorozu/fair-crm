"""Startup mail queue recovery tests."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.modules.mail_send_operations.application.process_mail_send_operations_worker import (
    MailSendOperationWorkerResult,
    set_mail_worker_session_factory,
)
from app.modules.mail_send_operations.application.startup_mail_queue_recovery import (
    _mail_queue_recovery_supervisor,
    run_mail_queue_startup_recovery,
    schedule_mail_queue_startup_recovery,
)
from app.modules.mail_send_operations.domain.value_objects import MailSendOperationStatus, MailSendSourceType
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
    SqlAlchemyMailSendOperationRepository,
)
from app.modules.email_delivery.domain.results import EmailDeliveryResult
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountSmtpConfigModel,
)
from app.shared.secret_encryption import encrypt_secret


def _create_smtp_account_row(db_session, organization_id, **kwargs):
    now = datetime.now(timezone.utc)
    account_id = kwargs.get("id") or uuid4()
    db_session.add(
        EmailAccountModel(
            id=account_id,
            organization_id=organization_id,
            name=kwargs.get("name", "SMTP"),
            account_type="smtp",
            provider_key=None,
            from_email=kwargs.get("from_email", "noreply@example.com"),
            from_name=None,
            is_default=kwargs.get("is_default", True),
            is_active=kwargs.get("is_active", True),
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        EmailAccountSmtpConfigModel(
            email_account_id=account_id,
            host=kwargs.get("host", "smtp.example.com"),
            port=kwargs.get("port", 587),
            username=kwargs.get("username", "smtp-user"),
            password=encrypt_secret(kwargs.get("password", "secret-password")),
            encryption_type=kwargs.get("encryption_type", "starttls"),
        )
    )
    db_session.flush()
    return account_id


def _create_smtp(db_session, organization_id):
    return _create_smtp_account_row(db_session, organization_id, name="Startup Recovery SMTP")


def _create_queued_operation(db_session, organization_id, *, recipient_email: str):
    repository = SqlAlchemyMailSendOperationRepository(db_session)
    account_id = _create_smtp(db_session, organization_id)
    record = repository.create(
        CreateMailSendOperationParams(
            organization_id=organization_id,
            source_type=MailSendSourceType.MANUAL_TASK_MAIL,
            recipient_email=recipient_email,
            subject="Startup recovery",
            body_text="Body",
            email_account_id=account_id,
        )
    )
    return db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == record.id).one()


@pytest.fixture
def recovery_session_factory(db_session):
    class _Factory:
        def __call__(self):
            return db_session

    set_mail_worker_session_factory(_Factory())
    try:
        yield
    finally:
        set_mail_worker_session_factory(None)


def test_startup_recovery_empty_queue_is_noop(db_session, recovery_session_factory):
    with patch(
        "app.modules.mail_send_operations.application.startup_mail_queue_recovery."
        "process_mail_send_operations_background"
    ) as mock_worker:
        result = run_mail_queue_startup_recovery()
    assert result is not None
    assert result.picked_count == 0
    mock_worker.assert_not_called()


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
    return_value=EmailDeliveryResult(success=True, transport="smtp"),
)
def test_startup_recovery_triggers_worker_for_queued(
    mock_send,
    db_session,
    organization_id,
    recovery_session_factory,
):
    operation = _create_queued_operation(
        db_session,
        organization_id,
        recipient_email="startup-queued@example.com",
    )

    result = run_mail_queue_startup_recovery()
    assert result is not None
    assert result.picked_count == 1
    assert result.sent_count == 1
    mock_send.assert_called_once()

    refreshed = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == operation.id).one()
    assert refreshed.status == MailSendOperationStatus.SENT
    events = [entry["event"] for entry in refreshed.operation_logs]
    assert "picked_by_worker" in events
    assert "sending_started" in events
    assert events[-1] == "sent"


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
    return_value=EmailDeliveryResult(success=True, transport="smtp"),
)
def test_startup_recovery_retryable_smtp_error_is_requeued(
    mock_send,
    db_session,
    organization_id,
    recovery_session_factory,
):
    mock_send.side_effect = SmtpMailDeliveryError("smtp down", error_type="SMTPConnectError")
    operation = _create_queued_operation(
        db_session,
        organization_id,
        recipient_email="startup-fail@example.com",
    )

    result = run_mail_queue_startup_recovery()
    assert result is not None
    assert result.failed_count == 1
    assert result.retried_count == 1
    mock_send.assert_called_once()

    refreshed = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == operation.id).one()
    assert refreshed.status == MailSendOperationStatus.QUEUED
    assert refreshed.retry_count == 2
    assert refreshed.error_code is None
    events = [entry["event"] for entry in refreshed.operation_logs]
    assert "sending_started" in events
    assert "failed" in events
    assert events[-1] == "auto_retry_scheduled"


def test_web_app_boot_does_not_run_mail_queue_recovery(monkeypatch):
    """Queued mail is owned by the standalone mail worker, not FastAPI startup."""
    monkeypatch.setenv("MAIL_STARTUP_RECOVERY_ENABLED", "true")
    get_settings.cache_clear()

    with patch(
        "app.modules.mail_send_operations.application.startup_mail_queue_recovery."
        "run_mail_queue_startup_recovery",
    ) as mock_recovery:
        with TestClient(create_app()) as client:
            assert client.get("/health").json()["status"] == "ok"
    mock_recovery.assert_not_called()
    get_settings.cache_clear()


def test_run_mail_queue_startup_recovery_swallows_worker_errors(recovery_session_factory):
    with patch(
        "app.modules.mail_send_operations.application.startup_mail_queue_recovery."
        "count_startup_recovery_candidates",
        return_value=(1, 0),
    ), patch(
        "app.modules.mail_send_operations.application.startup_mail_queue_recovery."
        "process_mail_send_operations_background",
        side_effect=RuntimeError("drain failed"),
    ):
        result = run_mail_queue_startup_recovery()
    assert result is None


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
    return_value=EmailDeliveryResult(success=True, transport="smtp"),
)
def test_repeated_startup_recovery_sends_once(
    mock_send,
    db_session,
    organization_id,
    recovery_session_factory,
):
    """Second recovery trigger must not SMTP-send an already processed operation."""
    operation = _create_queued_operation(
        db_session,
        organization_id,
        recipient_email="startup-once@example.com",
    )

    first = run_mail_queue_startup_recovery()
    second = run_mail_queue_startup_recovery()

    assert first is not None and first.sent_count == 1
    assert second is not None and second.picked_count == 0
    assert mock_send.call_count == 1

    refreshed = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == operation.id).one()
    assert refreshed.status == MailSendOperationStatus.SENT


def test_atomic_claim_rejects_second_pickup(db_session, organization_id):
    """Same queued row cannot be claimed twice (startup multi-instance safety)."""
    operation = _create_queued_operation(
        db_session,
        organization_id,
        recipient_email="claim-once@example.com",
    )
    repository = SqlAlchemyMailSendOperationRepository(db_session)
    now = datetime.now(timezone.utc)
    first = repository.try_claim_queued_operation(organization_id, operation.id, now=now)
    second = repository.try_claim_queued_operation(organization_id, operation.id, now=now)
    assert first is not None
    assert first.status == MailSendOperationStatus.SENDING
    assert second is None


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
    return_value=EmailDeliveryResult(success=True, transport="smtp"),
)
def test_recovery_skips_already_claimed_operation(
    mock_send,
    db_session,
    organization_id,
    recovery_session_factory,
):
    """A second instance seeing a claimed (sending) row must not SMTP-send it."""
    operation = _create_queued_operation(
        db_session,
        organization_id,
        recipient_email="startup-claimed@example.com",
    )
    repository = SqlAlchemyMailSendOperationRepository(db_session)
    claimed = repository.try_claim_queued_operation(
        organization_id,
        operation.id,
        now=datetime.now(timezone.utc),
    )
    assert claimed is not None

    result = run_mail_queue_startup_recovery()
    assert result is not None
    # Fresh claim: no longer queued, and not past timeout → empty drain / no send.
    assert result.picked_count == 0
    mock_send.assert_not_called()
    refreshed = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == operation.id).one()
    assert refreshed.status == MailSendOperationStatus.SENDING


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
    return_value=EmailDeliveryResult(success=True, transport="smtp"),
)
def test_startup_recovery_marks_stuck_sending_failed_without_resend(
    mock_send,
    db_session,
    organization_id,
    recovery_session_factory,
    monkeypatch,
):
    monkeypatch.setenv("MAIL_SENDING_TIMEOUT_MINUTES", "15")
    get_settings.cache_clear()

    stuck = _create_queued_operation(
        db_session,
        organization_id,
        recipient_email="startup-stuck@example.com",
    )
    stuck.status = MailSendOperationStatus.SENDING
    stuck.sending_started_at = datetime.now(timezone.utc) - timedelta(minutes=20)
    db_session.flush()

    result = run_mail_queue_startup_recovery()
    assert result is not None
    assert result.recovered_stuck_count == 1
    mock_send.assert_not_called()

    refreshed = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == stuck.id).one()
    assert refreshed.status == MailSendOperationStatus.FAILED
    assert refreshed.error_code == "sending_timeout"
    get_settings.cache_clear()


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
    return_value=EmailDeliveryResult(success=True, transport="smtp"),
)
def test_startup_recovery_leaves_sending_before_timeout(
    mock_send,
    db_session,
    organization_id,
    recovery_session_factory,
    monkeypatch,
):
    monkeypatch.setenv("MAIL_SENDING_TIMEOUT_MINUTES", "15")
    get_settings.cache_clear()

    stuck = _create_queued_operation(
        db_session,
        organization_id,
        recipient_email="startup-not-yet@example.com",
    )
    stuck.status = MailSendOperationStatus.SENDING
    stuck.sending_started_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.flush()

    with patch(
        "app.modules.mail_send_operations.application.startup_mail_queue_recovery."
        "process_mail_send_operations_background"
    ) as mock_worker:
        result = run_mail_queue_startup_recovery()

    assert result is not None
    assert result.recovered_stuck_count == 0
    mock_worker.assert_not_called()
    mock_send.assert_not_called()
    refreshed = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == stuck.id).one()
    assert refreshed.status == MailSendOperationStatus.SENDING
    get_settings.cache_clear()


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
    return_value=EmailDeliveryResult(success=True, transport="smtp"),
)
def test_startup_recovery_catches_orphan_after_timeout_elapses(
    mock_send,
    db_session,
    organization_id,
    recovery_session_factory,
    monkeypatch,
):
    """Early empty pass must not prevent a later pass once timeout has elapsed."""
    monkeypatch.setenv("MAIL_SENDING_TIMEOUT_MINUTES", "15")
    get_settings.cache_clear()

    stuck = _create_queued_operation(
        db_session,
        organization_id,
        recipient_email="startup-orphan-later@example.com",
    )
    stuck.status = MailSendOperationStatus.SENDING
    stuck.sending_started_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.flush()

    early = run_mail_queue_startup_recovery()
    assert early is not None
    assert early.recovered_stuck_count == 0
    still = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == stuck.id).one()
    assert still.status == MailSendOperationStatus.SENDING

    stuck.sending_started_at = datetime.now(timezone.utc) - timedelta(minutes=20)
    db_session.flush()

    later = run_mail_queue_startup_recovery()
    assert later is not None
    assert later.recovered_stuck_count == 1
    mock_send.assert_not_called()
    refreshed = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == stuck.id).one()
    assert refreshed.status == MailSendOperationStatus.FAILED
    assert refreshed.error_code == "sending_timeout"

    again = run_mail_queue_startup_recovery()
    assert again is not None
    assert again.recovered_stuck_count == 0
    mock_send.assert_not_called()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_recovery_supervisor_reruns_after_poll(monkeypatch):
    monkeypatch.setenv("MAIL_SENDING_TIMEOUT_MINUTES", "15")
    get_settings.cache_clear()
    calls = {"n": 0}

    def _recovery():
        calls["n"] += 1
        return MailSendOperationWorkerResult(0, 0, 0, 0, 0)

    async def _sleep(_seconds: float) -> None:
        if calls["n"] >= 2:
            raise asyncio.CancelledError()
        return None

    with patch(
        "app.modules.mail_send_operations.application.startup_mail_queue_recovery."
        "run_mail_queue_startup_recovery",
        side_effect=_recovery,
    ), patch(
        "app.modules.mail_send_operations.application.startup_mail_queue_recovery."
        "asyncio.sleep",
        side_effect=_sleep,
    ):
        with pytest.raises(asyncio.CancelledError):
            await _mail_queue_recovery_supervisor()

    assert calls["n"] >= 2
    get_settings.cache_clear()


def test_schedule_disabled_returns_none(monkeypatch):
    monkeypatch.setenv("MAIL_STARTUP_RECOVERY_ENABLED", "false")
    get_settings.cache_clear()
    assert schedule_mail_queue_startup_recovery() is None
    get_settings.cache_clear()

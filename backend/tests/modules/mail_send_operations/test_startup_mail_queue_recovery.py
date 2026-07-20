"""Startup mail queue recovery tests."""

from __future__ import annotations

import threading
import time
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
    run_mail_queue_startup_recovery,
    schedule_mail_queue_startup_recovery,
)
from app.modules.mail_send_operations.domain.value_objects import MailSendOperationStatus, MailSendSourceType
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
    SqlAlchemyMailSendOperationRepository,
)
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.smtp.infrastructure.persistence.models import SmtpAccountModel


def _create_smtp(db_session, organization_id):
    now = datetime.now(timezone.utc)
    account_id = uuid4()
    db_session.add(
        SmtpAccountModel(
            id=account_id,
            organization_id=organization_id,
            name="Startup Recovery SMTP",
            from_email="noreply@example.com",
            host="smtp.example.com",
            port=587,
            username="smtp-user",
            password="secret-password",
            encryption_type="starttls",
            is_default=True,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.flush()
    return account_id


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
            smtp_account_id=account_id,
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


@patch("app.modules.mail_send_operations.application.mail_send_operation_dispatcher.send_smtp_message")
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


@patch("app.modules.mail_send_operations.application.mail_send_operation_dispatcher.send_smtp_message")
def test_startup_recovery_queued_advances_to_failed_on_smtp_error(
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

    refreshed = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == operation.id).one()
    assert refreshed.status == MailSendOperationStatus.FAILED
    events = [entry["event"] for entry in refreshed.operation_logs]
    assert "sending_started" in events
    assert events[-1] == "failed"


def test_startup_recovery_does_not_block_app_boot(monkeypatch):
    monkeypatch.setenv("MAIL_STARTUP_RECOVERY_ENABLED", "true")
    get_settings.cache_clear()

    release = threading.Event()
    entered = threading.Event()

    def _slow_recovery():
        entered.set()
        release.wait(timeout=5)
        return MailSendOperationWorkerResult(0, 0, 0, 0, 0)

    with patch(
        "app.modules.mail_send_operations.application.startup_mail_queue_recovery."
        "run_mail_queue_startup_recovery",
        side_effect=_slow_recovery,
    ):
        started = time.monotonic()
        with TestClient(create_app()) as client:
            boot_elapsed = time.monotonic() - started
            assert boot_elapsed < 2.0
            assert client.get("/health").json()["status"] == "ok"
            assert entered.wait(timeout=2.0)
            release.set()
    get_settings.cache_clear()


def test_startup_recovery_worker_error_does_not_fail_boot(monkeypatch):
    monkeypatch.setenv("MAIL_STARTUP_RECOVERY_ENABLED", "true")
    get_settings.cache_clear()

    with patch(
        "app.modules.mail_send_operations.application.startup_mail_queue_recovery."
        "run_mail_queue_startup_recovery",
        side_effect=RuntimeError("recovery boom"),
    ):
        with TestClient(create_app()) as client:
            assert client.get("/health").status_code == 200
            assert client.get("/health").json()["status"] == "ok"
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


@patch("app.modules.mail_send_operations.application.mail_send_operation_dispatcher.send_smtp_message")
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


@patch("app.modules.mail_send_operations.application.mail_send_operation_dispatcher.send_smtp_message")
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


@patch("app.modules.mail_send_operations.application.mail_send_operation_dispatcher.send_smtp_message")
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


def test_schedule_disabled_returns_none(monkeypatch):
    monkeypatch.setenv("MAIL_STARTUP_RECOVERY_ENABLED", "false")
    get_settings.cache_clear()
    assert schedule_mail_queue_startup_recovery() is None
    get_settings.cache_clear()

"""BulkEmailHandler unit tests."""

from unittest.mock import MagicMock
from uuid import uuid4

from app.modules.operations.domain.value_objects import SourceKind
from app.modules.operations.infrastructure.handlers.bulk_email_handler import BulkEmailHandler


def test_bulk_email_handler_capabilities_supports_retry():
    handler = BulkEmailHandler()
    assert handler.capabilities.supports_retry is True
    assert handler.capabilities.supports_pause is False


def test_validate_create_fair_list_requires_fair_source():
    handler = BulkEmailHandler()
    result = handler.validate_create(
        source_kind=SourceKind.MANUAL_SELECTION,
        source_config={},
        type_config={
            "template_id": str(uuid4()),
            "smtp_account_id": str(uuid4()),
            "subject": "Hi",
            "source_type": "fair_list",
        },
        run_settings={},
    )
    assert not result.ok
    assert any("source_kind=fair" in err for err in result.errors)


def test_validate_create_manual_requires_emails():
    handler = BulkEmailHandler()
    result = handler.validate_create(
        source_kind=SourceKind.MANUAL_SELECTION,
        source_config={},
        type_config={
            "template_id": str(uuid4()),
            "smtp_account_id": str(uuid4()),
            "subject": "Hi",
            "source_type": "manual",
        },
        run_settings={},
    )
    assert not result.ok
    assert any("manual_emails" in err for err in result.errors)


def test_validate_create_manual_ok():
    handler = BulkEmailHandler()
    result = handler.validate_create(
        source_kind=SourceKind.NONE,
        source_config={},
        type_config={
            "template_id": str(uuid4()),
            "smtp_account_id": str(uuid4()),
            "subject": "Hi",
            "source_type": "manual",
            "manual_emails": "a@example.com",
        },
        run_settings={},
    )
    assert result.ok


def test_on_retry_only_failed(monkeypatch):
    batch_id = uuid4()
    org_id = uuid4()
    operation_id = uuid4()

    failed_outbox = MagicMock()
    failed_outbox.id = uuid4()
    failed_outbox.mail_send_operation_id = None
    failed_outbox.status = "failed"

    batch = MagicMock()
    batch.id = batch_id
    batch.fair_id = None
    batch.subject_override = "Konu"

    repo = MagicMock()
    repo.get_batch_by_operation_id.return_value = batch
    repo.list_failed_outbox.return_value = [failed_outbox]
    repo.get_batch.return_value = batch

    scheduled = []
    handler = BulkEmailHandler(
        batch_repository=repo,
        job_scheduler=lambda cmd: scheduled.append(cmd),
        mail_operation_sync=MagicMock(),
        session=MagicMock(),
    )

    operation = MagicMock()
    operation.id = operation_id
    operation.organization_id = org_id
    operation.latest_run_id = None

    run = MagicMock()
    run.id = uuid4()
    run.error_details = {}

    result = handler.on_retry(
        operation=operation,
        run=run,
        context=MagicMock(user_id=uuid4(), access_token="t"),
    )
    repo.prepare_outbox_for_retry.assert_called_once_with(failed_outbox.id)
    assert result.total_items == 1
    assert result.result_payload["retry_failed_only"] is True
    assert len(scheduled) == 1
    assert scheduled[0].batch_id == batch_id

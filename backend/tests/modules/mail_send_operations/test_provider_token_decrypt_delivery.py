"""Ensure encrypted MailerSend api_token is decrypted for MSO/worker and batch delivery."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountProviderConfigModel,
)
from app.modules.email_delivery.domain.exceptions import EmailDeliveryError
from app.modules.email_delivery.domain.results import EmailDeliveryResult
from app.modules.email_delivery.infrastructure.mailersend_adapter import MailerSendAdapter
from app.modules.fair_emails.application.commands import ProcessBatchCommand
from app.modules.fair_emails.application.process_batch import ProcessFairEmailBatchUseCase
from app.modules.fair_emails.infrastructure.persistence.models import (
    FairEmailBatchModel,
    FairEmailOutboxModel,
)
from app.modules.mail_send_operations.application.mail_send_operation_dispatcher import (
    MailSendOperationDispatcher,
)
from app.modules.mail_send_operations.application.process_mail_send_operations_worker import (
    ProcessMailSendOperationsWorker,
)
from app.modules.mail_send_operations.domain.value_objects import MailSendSourceType
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
    SqlAlchemyMailSendOperationRepository,
)
from app.shared.secret_encryption import encrypt_secret, is_encrypted_secret
from tests.modules.fair_emails.test_fair_bulk_email_api import _create_template


PLAINTEXT_TOKEN = "ms-live-token-for-decrypt-test"
MASKED_TOKEN = "••••••••"


def _create_provider_account(
    db_session,
    organization_id,
    *,
    api_token: str | None = PLAINTEXT_TOKEN,
    store_encrypted: bool = True,
    name: str = "MailerSend Test",
) -> UUID:
    now = datetime.now(tz=UTC)
    account_id = uuid4()
    db_session.add(
        EmailAccountModel(
            id=account_id,
            organization_id=organization_id,
            name=name,
            account_type="provider",
            provider_key="mailersend",
            from_email="noreply@example.com",
            from_name="FAIR CRM",
            is_default=False,
            is_active=True,
            created_at=now,
            updated_at=now,
            max_delivery_attempts=3,
        )
    )
    stored_token = ""
    if api_token:
        stored_token = encrypt_secret(api_token) if store_encrypted else api_token
    db_session.add(
        EmailAccountProviderConfigModel(
            email_account_id=account_id,
            provider_key="mailersend",
            config_json=json.dumps(
                {
                    "api_token": stored_token,
                    "from_email": "noreply@example.com",
                    "from_name": "FAIR CRM",
                }
            ),
            error_policy_json="{}",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.flush()
    if api_token and store_encrypted:
        stored = db_session.get(EmailAccountProviderConfigModel, account_id)
        assert stored is not None
        assert is_encrypted_secret(json.loads(stored.config_json)["api_token"])
        assert PLAINTEXT_TOKEN not in stored.config_json
    return account_id


def _create_queued_provider_operation(db_session, organization_id, email_account_id: UUID):
    repository = SqlAlchemyMailSendOperationRepository(db_session)
    record = repository.create(
        CreateMailSendOperationParams(
            organization_id=organization_id,
            source_type=MailSendSourceType.MANUAL_TASK_MAIL,
            recipient_email="provider-decrypt@example.com",
            subject="Provider decrypt",
            body_text="Body",
            email_account_id=email_account_id,
        )
    )
    return db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == record.id).one()


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
    return_value=EmailDeliveryResult(
        success=True,
        transport="provider:mailersend",
        external_message_id="msg-1",
        provider_status="accepted",
    ),
)
def test_mso_dispatcher_passes_decrypted_api_token(mock_send, db_session, organization_id):
    account_id = _create_provider_account(db_session, organization_id)
    operation = _create_queued_provider_operation(db_session, organization_id, account_id)
    record = SqlAlchemyMailSendOperationRepository(db_session).get_by_id(
        organization_id,
        operation.id,
    )
    assert record is not None

    MailSendOperationDispatcher(db_session).dispatch(record)

    mock_send.assert_called_once()
    kwargs = mock_send.call_args.kwargs
    assert kwargs["provider_config"]["api_token"] == PLAINTEXT_TOKEN
    assert not is_encrypted_secret(kwargs["provider_config"]["api_token"])
    assert kwargs["provider_config"]["from_email"] == "noreply@example.com"


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
    return_value=EmailDeliveryResult(
        success=True,
        transport="provider:mailersend",
        external_message_id="msg-worker",
        provider_status="accepted",
    ),
)
def test_worker_passes_decrypted_api_token_to_dispatcher(mock_send, db_session, organization_id):
    account_id = _create_provider_account(db_session, organization_id, name="Worker Provider")
    _create_queued_provider_operation(db_session, organization_id, account_id)

    result = ProcessMailSendOperationsWorker(db_session).run()
    assert result.picked_count == 1
    assert result.sent_count == 1
    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["provider_config"]["api_token"] == PLAINTEXT_TOKEN


def test_mailersend_adapter_rejects_missing_token():
    adapter = MailerSendAdapter()
    account = type(
        "A",
        (),
        {
            "id": uuid4(),
            "provider_key": "mailersend",
            "from_email": "a@b.com",
            "from_name": "n",
        },
    )()
    with pytest.raises(EmailDeliveryError) as exc_info:
        adapter.send(
            account,
            recipient="to@example.com",
            subject="x",
            body_html=None,
            body_text="x",
            provider_config={"api_token": "", "from_email": "a@b.com", "from_name": "n"},
        )
    assert exc_info.value.error_code == "MissingApiToken"
    assert "MailerSend API token is not configured" in str(exc_info.value)


def test_mailersend_adapter_rejects_masked_token_as_missing():
    """Masked UI placeholders must not be treated as a usable API token."""
    adapter = MailerSendAdapter()
    account = type(
        "A",
        (),
        {
            "id": uuid4(),
            "provider_key": "mailersend",
            "from_email": "a@b.com",
            "from_name": "n",
        },
    )()
    # Blank / whitespace-only still MissingApiToken; masked bullets are non-empty
    # but must never be loaded from DB as the real secret (decrypt path never stores them).
    with pytest.raises(EmailDeliveryError) as exc_info:
        adapter.send(
            account,
            recipient="to@example.com",
            subject="x",
            body_html=None,
            body_text="x",
            provider_config={"api_token": "   ", "from_email": "a@b.com", "from_name": "n"},
        )
    assert exc_info.value.error_code == "MissingApiToken"
    assert MASKED_TOKEN != PLAINTEXT_TOKEN


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
    return_value=EmailDeliveryResult(
        success=True,
        transport="provider:mailersend",
        external_message_id="msg-batch",
        provider_status="accepted",
    ),
)
def test_process_batch_passes_decrypted_provider_config(
    mock_send,
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    account_id = _create_provider_account(db_session, organization_id, name="Batch Provider")
    template_id = _create_template(client, auth_headers, key=f"provider_batch_{uuid4().hex[:8]}")
    now = datetime.now(tz=UTC)
    batch_id = uuid4()
    db_session.add(
        FairEmailBatchModel(
            id=batch_id,
            organization_id=organization_id,
            fair_id=None,
            template_id=UUID(template_id),
            email_account_id=account_id,
            subject_override="Provider batch",
            recipient_options_json={},
            status="queued",
            total_count=1,
            sent_count=0,
            failed_count=0,
            skipped_count=0,
            created_by_user_id=user_id,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        FairEmailOutboxModel(
            id=uuid4(),
            batch_id=batch_id,
            organization_id=organization_id,
            customer_id=None,
            contact_id=None,
            participation_id=None,
            recipient_name="Recipient",
            company_name="",
            email="batch-provider@example.com",
            source="manual",
            status="pending",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    ProcessFairEmailBatchUseCase(db_session).execute(
        ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
    )

    mock_send.assert_called()
    kwargs = mock_send.call_args.kwargs
    assert kwargs["provider_config"]["api_token"] == PLAINTEXT_TOKEN
    assert not is_encrypted_secret(kwargs["provider_config"]["api_token"])


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
    return_value=EmailDeliveryResult(success=True, transport="smtp"),
)
def test_smtp_worker_path_unchanged_without_provider_config(mock_send, db_session, organization_id):
    from tests.modules.mail_send_operations.test_mail_send_operations_worker import (
        _create_queued_operation,
    )

    _create_queued_operation(
        db_session,
        organization_id,
        source_type=MailSendSourceType.MANUAL_TASK_MAIL,
        recipient_email="smtp-unchanged@example.com",
    )
    result = ProcessMailSendOperationsWorker(db_session).run()
    assert result.sent_count == 1
    mock_send.assert_called_once()
    kwargs = mock_send.call_args.kwargs
    assert kwargs.get("provider_config") is None
    assert kwargs["smtp_config"] is not None
    assert kwargs["smtp_config"].password == "secret-password"

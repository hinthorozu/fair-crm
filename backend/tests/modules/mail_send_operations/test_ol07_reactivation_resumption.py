"""OL-07 deterministic mail/provider behavior after organization reactivation."""

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.integrations.kyrox_core.lifecycle import OrganizationWorkNotAllowedError
from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountProviderConfigModel,
)
from app.modules.email_delivery.application.email_delivery_service import EmailDeliveryService
from app.modules.email_delivery.domain.results import EmailDeliveryResult
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
from app.shared.secret_encryption import encrypt_secret, is_encrypted_secret


def _create_provider_account(db_session, organization_id: UUID) -> UUID:
    now = datetime.now(tz=UTC)
    account_id = uuid4()
    encrypted = encrypt_secret("ol07-reactivation-token")
    db_session.add(
        EmailAccountModel(
            id=account_id,
            organization_id=organization_id,
            name="OL07 Reactivation Provider",
            account_type="provider",
            provider_key="mailersend",
            from_email="noreply@example.com",
            from_name="FAIR",
            is_default=False,
            is_active=True,
            created_at=now,
            updated_at=now,
            max_delivery_attempts=3,
        )
    )
    db_session.add(
        EmailAccountProviderConfigModel(
            email_account_id=account_id,
            provider_key="mailersend",
            config_json=json.dumps(
                {
                    "api_token": encrypted,
                    "from_email": "noreply@example.com",
                    "from_name": "FAIR",
                }
            ),
            error_policy_json="{}",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.flush()
    return account_id


def _mail_params(organization_id: UUID, *, subject: str) -> CreateMailSendOperationParams:
    return CreateMailSendOperationParams(
        organization_id=organization_id,
        source_type=MailSendSourceType.MANUAL_EMAIL,
        recipient_email="reactivation@example.com",
        subject=subject,
        body_text="OL-07 reactivation contract",
    )


def test_cancelled_mail_stays_terminal_while_new_mail_is_worker_eligible(
    db_session,
    organization_id,
):
    repository = SqlAlchemyMailSendOperationRepository(db_session)
    service = MailSendOperationService(repository)

    cancelled = service.create_mail_send_operation(
        _mail_params(organization_id, subject="cancelled-before-reactivation"),
        check_consent=False,
    )
    service.mark_cancelled(
        organization_id,
        cancelled.id,
        message="organization_lifecycle_prestart_cancelled:suspended",
    )

    # Reactivation permits newly queued product work; it must not mutate or
    # resurrect the previously terminalized mail operation.
    fresh = service.create_mail_send_operation(
        _mail_params(organization_id, subject="new-after-reactivation"),
        check_consent=False,
    )
    db_session.commit()

    ready = repository.list_queued_for_worker(
        max_batch_size=10,
        now=datetime.now(tz=UTC) + timedelta(seconds=1),
    )
    retryable = repository.list_failed_for_auto_retry(
        max_batch_size=10,
        now=datetime.now(tz=UTC) + timedelta(seconds=1),
    )

    assert [record.id for record in ready] == [fresh.id]
    assert cancelled.id not in {record.id for record in retryable}
    persisted_cancelled = repository.get_by_id(organization_id, cancelled.id)
    assert persisted_cancelled is not None
    assert persisted_cancelled.status == MailSendOperationStatus.CANCELLED


def test_uncertain_handoff_remains_non_auto_retry_after_reactivation(
    db_session,
    organization_id,
):
    repository = SqlAlchemyMailSendOperationRepository(db_session)
    service = MailSendOperationService(repository)
    operation = service.create_mail_send_operation(
        _mail_params(organization_id, subject="uncertain-before-reactivation"),
        check_consent=False,
    )
    service.mark_failed(
        organization_id,
        operation.id,
        error_code="provider_handoff_uncertain",
        error_message="provider acceptance unknown",
    )
    db_session.commit()

    persisted = repository.get_by_id(organization_id, operation.id)
    assert persisted is not None
    assert persisted.metadata_json["auto_retry_pending"] is False
    retryable = repository.list_failed_for_auto_retry(
        max_batch_size=10,
        now=datetime.now(tz=UTC) + timedelta(seconds=1),
    )
    assert operation.id not in {record.id for record in retryable}


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
    return_value=EmailDeliveryResult(
        success=True,
        transport="provider:mailersend",
        external_message_id="reactivated-message",
        provider_status="accepted",
    ),
)
def test_reactivation_allows_new_provider_handoff_without_credential_reenable(
    mock_send,
    db_session,
    organization_id,
):
    account_id = _create_provider_account(db_session, organization_id)
    guard = MagicMock()
    guard.require_work_allowed.side_effect = [
        OrganizationWorkNotAllowedError(
            "Organization lifecycle does not allow product work: suspended"
        ),
        SimpleNamespace(
            organization_id=organization_id,
            status="active",
            work_allowed=True,
        ),
    ]
    service = EmailDeliveryService(db_session, lifecycle_guard=guard)

    with pytest.raises(OrganizationWorkNotAllowedError):
        service.send(
            organization_id=organization_id,
            email_account_id=account_id,
            to="blocked@example.com",
            subject="blocked while suspended",
            body_text="body",
        )
    mock_send.assert_not_called()

    result = service.send(
        organization_id=organization_id,
        email_account_id=account_id,
        to="new@example.com",
        subject="new after reactivation",
        body_text="body",
    )

    assert result.external_message_id == "reactivated-message"
    mock_send.assert_called_once()
    account = db_session.get(EmailAccountModel, account_id)
    provider_config = db_session.get(EmailAccountProviderConfigModel, account_id)
    assert account is not None and account.is_active is True
    assert provider_config is not None
    assert is_encrypted_secret(json.loads(provider_config.config_json)["api_token"])
    assert mock_send.call_args.kwargs["provider_config"]["api_token"] == "ol07-reactivation-token"

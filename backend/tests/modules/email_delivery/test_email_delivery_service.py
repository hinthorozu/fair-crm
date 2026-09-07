"""Central EmailDeliveryService — account/config/secret resolve gateway."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleUnavailableError,
    OrganizationWorkNotAllowedError,
)
from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountProviderConfigModel,
    EmailAccountSmtpConfigModel,
)
from app.modules.email_delivery.application.email_delivery_service import EmailDeliveryService
from app.modules.email_delivery.domain.results import EmailDeliveryResult
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.shared.secret_encryption import encrypt_secret, is_encrypted_secret


def _create_smtp_account(db_session, organization_id, *, password: str = "smtp-secret") -> UUID:
    now = datetime.now(tz=UTC)
    account_id = uuid4()
    db_session.add(
        EmailAccountModel(
            id=account_id,
            organization_id=organization_id,
            name="SMTP Central",
            account_type="smtp",
            provider_key=None,
            from_email="smtp@example.com",
            from_name=None,
            is_default=True,
            is_active=True,
            created_at=now,
            updated_at=now,
            max_delivery_attempts=3,
        )
    )
    db_session.add(
        EmailAccountSmtpConfigModel(
            email_account_id=account_id,
            host="smtp.example.com",
            port=587,
            username="user",
            password=encrypt_secret(password),
            encryption_type="starttls",
        )
    )
    db_session.flush()
    return account_id


def _create_provider_account(
    db_session,
    organization_id,
    *,
    api_token: str = "ms-central-token",
) -> UUID:
    now = datetime.now(tz=UTC)
    account_id = uuid4()
    db_session.add(
        EmailAccountModel(
            id=account_id,
            organization_id=organization_id,
            name="Provider Central",
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
    encrypted = encrypt_secret(api_token)
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
    assert is_encrypted_secret(encrypted)
    return account_id


def _active_lifecycle_guard(organization_id: UUID) -> MagicMock:
    guard = MagicMock()
    guard.require_work_allowed.return_value = SimpleNamespace(
        organization_id=organization_id,
        status="active",
        work_allowed=True,
    )
    return guard


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
    return_value=EmailDeliveryResult(success=True, transport="smtp"),
)
def test_central_service_smtp_decrypts_password(mock_send, db_session, organization_id):
    account_id = _create_smtp_account(db_session, organization_id, password="smtp-secret")
    lifecycle_guard = _active_lifecycle_guard(organization_id)
    EmailDeliveryService(db_session, lifecycle_guard=lifecycle_guard).send(
        organization_id=organization_id,
        email_account_id=account_id,
        to="to@example.com",
        subject="SMTP",
        body_text="body",
    )
    lifecycle_guard.require_work_allowed.assert_called_once_with(organization_id)
    mock_send.assert_called_once()
    kwargs = mock_send.call_args.kwargs
    assert kwargs["smtp_config"].password == "smtp-secret"
    assert kwargs.get("provider_config") in (None, {})


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
    return_value=EmailDeliveryResult(
        success=True,
        transport="provider:mailersend",
        external_message_id="msg-central",
        provider_status="accepted",
    ),
)
def test_central_service_provider_decrypts_api_token(mock_send, db_session, organization_id):
    account_id = _create_provider_account(db_session, organization_id, api_token="ms-central-token")
    lifecycle_guard = _active_lifecycle_guard(organization_id)
    result = EmailDeliveryService(db_session, lifecycle_guard=lifecycle_guard).send(
        organization_id=organization_id,
        email_account_id=account_id,
        to="to@example.com",
        subject="Provider",
        body_text="body",
    )
    lifecycle_guard.require_work_allowed.assert_called_once_with(organization_id)
    assert result.external_message_id == "msg-central"
    assert result.provider_status == "accepted"
    kwargs = mock_send.call_args.kwargs
    assert kwargs["provider_config"]["api_token"] == "ms-central-token"
    assert not is_encrypted_secret(kwargs["provider_config"]["api_token"])


@patch("app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send")
def test_suspended_organization_cannot_reach_provider_and_secret_stays_persisted(
    mock_send,
    db_session,
    organization_id,
):
    account_id = _create_provider_account(db_session, organization_id, api_token="ms-central-token")
    lifecycle_guard = MagicMock()
    lifecycle_guard.require_work_allowed.side_effect = OrganizationWorkNotAllowedError(
        "Organization lifecycle does not allow product work: suspended"
    )

    with pytest.raises(OrganizationWorkNotAllowedError):
        EmailDeliveryService(db_session, lifecycle_guard=lifecycle_guard).send(
            organization_id=organization_id,
            email_account_id=account_id,
            to="to@example.com",
            subject="Blocked",
            body_text="body",
        )

    mock_send.assert_not_called()
    account = db_session.get(EmailAccountModel, account_id)
    provider_config = db_session.get(EmailAccountProviderConfigModel, account_id)
    assert account is not None and account.is_active is True
    assert provider_config is not None
    persisted_token = json.loads(provider_config.config_json)["api_token"]
    assert is_encrypted_secret(persisted_token)


@patch("app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send")
def test_lifecycle_unavailable_fails_closed_without_provider_or_account_mutation(
    mock_send,
    db_session,
    organization_id,
):
    account_id = _create_provider_account(db_session, organization_id, api_token="ms-central-token")
    lifecycle_guard = MagicMock()
    lifecycle_guard.require_work_allowed.side_effect = OrganizationLifecycleUnavailableError(
        "Organization lifecycle authority unavailable"
    )

    with pytest.raises(OrganizationLifecycleUnavailableError):
        EmailDeliveryService(db_session, lifecycle_guard=lifecycle_guard).send(
            organization_id=organization_id,
            email_account_id=account_id,
            to="to@example.com",
            subject="Deferred",
            body_text="body",
        )

    mock_send.assert_not_called()
    account = db_session.get(EmailAccountModel, account_id)
    provider_config = db_session.get(EmailAccountProviderConfigModel, account_id)
    assert account is not None and account.is_active is True
    assert provider_config is not None
    persisted_token = json.loads(provider_config.config_json)["api_token"]
    assert is_encrypted_secret(persisted_token)


def test_central_service_inactive_account_raises(db_session, organization_id):
    account_id = _create_smtp_account(db_session, organization_id)
    model = db_session.get(EmailAccountModel, account_id)
    assert model is not None
    model.is_active = False
    db_session.flush()
    with pytest.raises(SmtpMailDeliveryError) as exc_info:
        EmailDeliveryService(
            db_session,
            lifecycle_guard=_active_lifecycle_guard(organization_id),
        ).send(
            organization_id=organization_id,
            email_account_id=account_id,
            to="to@example.com",
            subject="x",
            body_text="x",
        )
    assert exc_info.value.error_type == "InactiveAccount"


def test_central_service_missing_account_raises(db_session, organization_id):
    with pytest.raises(SmtpMailDeliveryError) as exc_info:
        EmailDeliveryService(
            db_session,
            lifecycle_guard=_active_lifecycle_guard(organization_id),
        ).send(
            organization_id=organization_id,
            email_account_id=uuid4(),
            to="to@example.com",
            subject="x",
            body_text="x",
        )
    assert exc_info.value.error_type == "EmailAccountNotFound"

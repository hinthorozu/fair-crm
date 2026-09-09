from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountProviderConfigModel,
)
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)
from app.modules.organization_closure.api.lifecycle_signal_routes import (
    require_lifecycle_signal_credential,
)
from app.modules.organization_closure.application.suspension_security import (
    OrganizationSuspensionSecurityService,
)
from app.shared.secret_encryption import encrypt_secret


class FakeLifecycle:
    def __init__(self, *, status: str, updated_at: datetime) -> None:
        self.status = status
        self.updated_at = updated_at
        self.calls: list[object] = []

    def get_snapshot(self, organization_id: object) -> SimpleNamespace:
        self.calls.append(organization_id)
        return SimpleNamespace(status=self.status, updated_at=self.updated_at)


def _mailersend_account(db_session, organization_id):
    now = datetime.now(tz=UTC)
    account = EmailAccountModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Suspension MailerSend",
        account_type="provider",
        provider_key="mailersend",
        from_email="provider@example.com",
        from_name="Provider",
        is_default=False,
        is_active=True,
        max_delivery_attempts=3,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    config = EmailAccountProviderConfigModel(
        email_account_id=account.id,
        provider_key="mailersend",
        config_json=json.dumps(
            {
                "api_token": encrypt_secret("mailersend-api-secret"),
                "from_email": "provider@example.com",
                "from_name": "Provider",
                "webhook_signing_secret": encrypt_secret("webhook-secret"),
            }
        ),
        error_policy_json="{}",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([account, config])
    db_session.flush()
    return account


def test_current_suspension_episode_zeroizes_signing_secret_idempotently(
    db_session,
    organization_id,
) -> None:
    account = _mailersend_account(db_session, organization_id)
    episode = datetime.now(tz=UTC)
    repository = SqlAlchemyEmailAccountRepository(db_session)
    lifecycle = FakeLifecycle(status="suspended", updated_at=episode)
    service = OrganizationSuspensionSecurityService(repository, lifecycle)

    first = service.apply(
        organization_id=organization_id,
        lifecycle_updated_at=episode,
    )
    second = service.apply(
        organization_id=organization_id,
        lifecycle_updated_at=episode,
    )

    config = repository.get_provider_config(
        account.id,
        organization_id=organization_id,
    )
    assert config is not None
    assert config.config["api_token"] == "mailersend-api-secret"
    assert config.config["webhook_signing_secret"] == ""
    assert first.outcome == "applied"
    assert first.zeroized_signing_secrets == 1
    assert second.outcome == "applied"
    assert second.zeroized_signing_secrets == 0
    assert lifecycle.calls == [organization_id, organization_id]


def test_stale_suspension_episode_does_not_touch_current_secret(
    db_session,
    organization_id,
) -> None:
    account = _mailersend_account(db_session, organization_id)
    current_episode = datetime.now(tz=UTC)
    stale_episode = current_episode - timedelta(minutes=5)
    repository = SqlAlchemyEmailAccountRepository(db_session)
    service = OrganizationSuspensionSecurityService(
        repository,
        FakeLifecycle(status="suspended", updated_at=current_episode),
    )

    result = service.apply(
        organization_id=organization_id,
        lifecycle_updated_at=stale_episode,
    )

    config = repository.get_provider_config(
        account.id,
        organization_id=organization_id,
    )
    assert config is not None
    assert config.config["webhook_signing_secret"] == "webhook-secret"
    assert result.outcome == "stale_ignored"
    assert result.zeroized_signing_secrets == 0


def test_reactivated_organization_ignores_delayed_suspension_signal(
    db_session,
    organization_id,
) -> None:
    account = _mailersend_account(db_session, organization_id)
    episode = datetime.now(tz=UTC)
    repository = SqlAlchemyEmailAccountRepository(db_session)
    service = OrganizationSuspensionSecurityService(
        repository,
        FakeLifecycle(status="active", updated_at=episode),
    )

    result = service.apply(
        organization_id=organization_id,
        lifecycle_updated_at=episode,
    )

    config = repository.get_provider_config(
        account.id,
        organization_id=organization_id,
    )
    assert config is not None
    assert config.config["webhook_signing_secret"] == "webhook-secret"
    assert result.outcome == "stale_ignored"
    assert result.zeroized_signing_secrets == 0


def test_signal_credential_fails_closed_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FAIR_CRM_CORE_LIFECYCLE_SIGNAL_TOKEN", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        require_lifecycle_signal_credential("anything")

    assert exc_info.value.status_code == 503


def test_signal_credential_rejects_wrong_token_and_accepts_exact_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FAIR_CRM_CORE_LIFECYCLE_SIGNAL_TOKEN", "signal-secret")

    with pytest.raises(HTTPException) as exc_info:
        require_lifecycle_signal_credential("wrong")
    assert exc_info.value.status_code == 401

    require_lifecycle_signal_credential("signal-secret")

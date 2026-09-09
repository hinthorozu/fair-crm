from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleGuard,
    OrganizationLifecycleUnavailableError,
    OrganizationWorkNotAllowedError,
)
from app.modules.email_accounts.infrastructure.persistence.models import EmailAccountModel
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)
from app.modules.email_webhooks.application.mailersend_signature import (
    MAILERSEND_WEBHOOK_TEST_SIGNING_SECRET,
    compute_mailersend_signature,
)


def _create_account(db_session, organization_id):
    now = datetime.now(tz=UTC)
    account_id = uuid4()
    db_session.add(
        EmailAccountModel(
            id=account_id,
            organization_id=organization_id,
            name="OL09-B lifecycle ingress",
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
    db_session.commit()
    return account_id


def _post(client, account_id, payload, secret="not-used-after-cutoff"):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = compute_mailersend_signature(raw_body=body, signing_secret=secret)
    return client.post(
        f"/api/v1/webhooks/email/mailersend/{account_id}",
        content=body,
        headers={"Signature": signature},
    )


def _normal_payload():
    return {
        "type": "activity.delivered",
        "created_at": "2026-09-09T17:00:00Z",
        "data": {"message_id": "ol09b-message"},
    }


def _forbid_provider_config_access(*args, **kwargs):
    raise AssertionError("provider config/signing secret must not be read after lifecycle cutoff")


def test_suspended_organization_is_acked_and_dropped_before_secret_access(
    client,
    db_session,
    organization_id,
    monkeypatch,
):
    account_id = _create_account(db_session, organization_id)

    def _suspended(self, requested_organization_id):
        assert requested_organization_id == organization_id
        raise OrganizationWorkNotAllowedError("suspended")

    monkeypatch.setattr(OrganizationLifecycleGuard, "require_work_allowed", _suspended)
    monkeypatch.setattr(
        SqlAlchemyEmailAccountRepository,
        "get_provider_config",
        _forbid_provider_config_access,
    )

    response = _post(client, account_id, _normal_payload())

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "outcome": "ignored",
        "detail": "organization_work_not_allowed",
    }


def test_unavailable_lifecycle_authority_is_acked_and_dropped_before_secret_access(
    client,
    db_session,
    organization_id,
    monkeypatch,
):
    account_id = _create_account(db_session, organization_id)

    def _unavailable(self, requested_organization_id):
        assert requested_organization_id == organization_id
        raise OrganizationLifecycleUnavailableError("authority unavailable")

    monkeypatch.setattr(OrganizationLifecycleGuard, "require_work_allowed", _unavailable)
    monkeypatch.setattr(
        SqlAlchemyEmailAccountRepository,
        "get_provider_config",
        _forbid_provider_config_access,
    )

    response = _post(client, account_id, _normal_payload())

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "outcome": "ignored",
        "detail": "lifecycle_authority_unavailable",
    }


def test_webhook_test_ping_does_not_require_tenant_lifecycle_authority(
    client,
    monkeypatch,
):
    def _must_not_run(self, organization_id):
        raise AssertionError("webhook.test must not enter tenant lifecycle authorization")

    monkeypatch.setattr(OrganizationLifecycleGuard, "require_work_allowed", _must_not_run)

    payload = {
        "type": "webhook.test",
        "message": "This is a ping test message",
        "created_at": "2026-09-09T17:00:00Z",
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = compute_mailersend_signature(
        raw_body=body,
        signing_secret=MAILERSEND_WEBHOOK_TEST_SIGNING_SECRET,
    )

    response = client.post(
        f"/api/v1/webhooks/email/mailersend/{uuid4()}",
        content=body,
        headers={"Signature": signature},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "outcome": "test_ok",
        "detail": "webhook.test",
    }

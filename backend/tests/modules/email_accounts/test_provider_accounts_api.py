"""Provider account create/read/mask API tests."""

from __future__ import annotations

from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountProviderConfigModel,
)
from app.shared.secret_encryption import is_encrypted_secret


def _provider_payload(**overrides):
    payload = {
        "name": "MailerSend Main",
        "account_type": "provider",
        "provider_key": "mailersend",
        "is_default": False,
        "is_active": True,
        "max_delivery_attempts": 3,
        "provider_config": {
            "api_token": "ms-secret-token",
            "from_email": "noreply@example.com",
            "from_name": "FAIR CRM",
        },
        "error_policy": {
            "groups": [
                {
                    "category": "ACCOUNT_ERROR",
                    "identifiers": ["401", "403"],
                    "action": "deactivate_and_fail",
                },
                {
                    "category": "DELIVERY_ERROR",
                    "identifiers": ["429", "503"],
                    "action": "auto_retry",
                },
                {
                    "category": "MESSAGE_ERROR",
                    "identifiers": ["422"],
                    "action": "fail",
                },
            ]
        },
    }
    payload.update(overrides)
    return payload


def test_list_providers_includes_mailersend(client, auth_headers):
    response = client.get("/api/v1/email-accounts/providers", headers=auth_headers)
    assert response.status_code == 200
    keys = [item["provider_key"] for item in response.json()["items"]]
    assert "mailersend" in keys
    mailersend = next(item for item in response.json()["items"] if item["provider_key"] == "mailersend")
    field_keys = {field["key"] for field in mailersend["fields"]}
    assert {"api_token", "from_email", "from_name", "webhook_signing_secret"} <= field_keys


def test_create_provider_account_masks_token(client, auth_headers, db_session):
    response = client.post(
        "/api/v1/email-accounts",
        json=_provider_payload(),
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["account_type"] == "provider"
    assert body["provider_key"] == "mailersend"
    assert body["from_email"] == "noreply@example.com"
    assert body["provider_config"]["api_token"] is None
    assert body["secrets_set"]["api_token"] is True
    assert body["host"] is None

    from uuid import UUID

    stored = db_session.get(EmailAccountProviderConfigModel, UUID(body["id"]))
    assert stored is not None
    assert "ms-secret-token" not in stored.config_json
    assert is_encrypted_secret(
        __import__("json").loads(stored.config_json)["api_token"]
    )


def test_update_provider_preserves_token_when_blank(client, auth_headers):
    created = client.post(
        "/api/v1/email-accounts",
        json=_provider_payload(name="Preserve Token"),
        headers=auth_headers,
    )
    assert created.status_code == 201
    account_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/email-accounts/{account_id}",
        json={
            "provider_config": {
                "api_token": "",
                "from_email": "changed@example.com",
                "from_name": "Changed",
            }
        },
        headers=auth_headers,
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["from_email"] == "changed@example.com"
    assert body["secrets_set"]["api_token"] is True
    assert body["provider_config"]["api_token"] is None


def test_update_provider_can_change_max_delivery_attempts(client, auth_headers, db_session):
    created = client.post(
        "/api/v1/email-accounts",
        json=_provider_payload(name="Provider attempts", max_delivery_attempts=2),
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    account_id = created.json()["id"]
    assert created.json()["max_delivery_attempts"] == 2

    updated = client.patch(
        f"/api/v1/email-accounts/{account_id}",
        json={"max_delivery_attempts": 5},
        headers=auth_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["max_delivery_attempts"] == 5

    from uuid import UUID

    from app.modules.email_accounts.infrastructure.persistence.models import EmailAccountModel

    model = db_session.get(EmailAccountModel, UUID(account_id))
    assert model is not None
    assert model.max_delivery_attempts == 5


def test_error_policy_rejects_cross_group_duplicates(client, auth_headers):
    response = client.post(
        "/api/v1/email-accounts",
        json=_provider_payload(
            error_policy={
                "groups": [
                    {
                        "category": "ACCOUNT_ERROR",
                        "identifiers": ["401"],
                        "action": "fail",
                    },
                    {
                        "category": "DELIVERY_ERROR",
                        "identifiers": ["401"],
                        "action": "auto_retry",
                    },
                    {
                        "category": "MESSAGE_ERROR",
                        "identifiers": [],
                        "action": "fail",
                    },
                ]
            }
        ),
        headers=auth_headers,
    )
    assert response.status_code == 400

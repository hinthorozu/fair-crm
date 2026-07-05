from uuid import UUID, uuid4

from app.integrations.kyrox_core.auth import create_test_token
from app.modules.smtp.infrastructure.persistence.models import SmtpAccountModel


def _smtp_payload(**overrides):
    payload = {
        "name": "Primary SMTP",
        "from_email": "noreply@example.com",
        "from_name": "FAIR CRM",
        "host": "smtp.example.com",
        "port": 587,
        "username": "smtp-user",
        "password": "secret-password",
        "encryption_type": "starttls",
        "is_default": False,
        "is_active": True,
    }
    payload.update(overrides)
    return payload


def _create_smtp_account(client, auth_headers, **overrides):
    return client.post(
        "/api/v1/smtp/accounts",
        json=_smtp_payload(**overrides),
        headers=auth_headers,
    )


def test_create_smtp_account(client, auth_headers, organization_id):
    response = _create_smtp_account(client, auth_headers, name="Outbound Mail")
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Outbound Mail"
    assert body["organization_id"] == str(organization_id)
    assert body["is_default"] is True
    assert body["has_password"] is True
    assert "password" not in body


def test_first_smtp_account_is_auto_default(client, auth_headers):
    response = _create_smtp_account(client, auth_headers, is_default=False)
    assert response.status_code == 201
    assert response.json()["is_default"] is True


def test_only_one_default_smtp_account_per_organization(client, auth_headers):
    first = _create_smtp_account(client, auth_headers, name="First SMTP")
    second = _create_smtp_account(client, auth_headers, name="Second SMTP", is_default=True)
    assert first.status_code == 201
    assert second.status_code == 201

    list_response = client.get("/api/v1/smtp/accounts", headers=auth_headers)
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    defaults = [item for item in items if item["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["name"] == "Second SMTP"

    first_after = client.get(f"/api/v1/smtp/accounts/{first.json()['id']}", headers=auth_headers)
    assert first_after.json()["is_default"] is False


def test_cannot_access_smtp_account_from_other_organization(
    client,
    auth_headers,
    other_organization_id,
    user_id,
):
    create_response = _create_smtp_account(client, auth_headers)
    account_id = create_response.json()["id"]

    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    get_response = client.get(f"/api/v1/smtp/accounts/{account_id}", headers=other_headers)
    assert get_response.status_code == 404


def test_list_response_does_not_include_password(client, auth_headers):
    _create_smtp_account(client, auth_headers)
    response = client.get("/api/v1/smtp/accounts", headers=auth_headers)
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert "password" not in item
        assert item["has_password"] is True


def test_update_password_empty_keeps_existing(client, auth_headers, db_session):
    create_response = _create_smtp_account(client, auth_headers, password="keep-me")
    account_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/smtp/accounts/{account_id}",
        json={"name": "Renamed SMTP", "password": ""},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Renamed SMTP"
    assert update_response.json()["has_password"] is True

    model = db_session.get(SmtpAccountModel, UUID(account_id))
    assert model is not None
    assert model.password == "keep-me"


def test_update_password_replaces_existing(client, auth_headers, db_session):
    create_response = _create_smtp_account(client, auth_headers, password="old-secret")
    account_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/smtp/accounts/{account_id}",
        json={"password": "new-secret"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200

    model = db_session.get(SmtpAccountModel, UUID(account_id))
    assert model is not None
    assert model.password == "new-secret"


def test_set_default_rejects_inactive_account(client, auth_headers):
    create_response = _create_smtp_account(client, auth_headers, name="Inactive SMTP")
    account_id = create_response.json()["id"]

    deactivate_response = client.patch(
        f"/api/v1/smtp/accounts/{account_id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert deactivate_response.status_code == 200

    set_default_response = client.post(
        f"/api/v1/smtp/accounts/{account_id}/set-default",
        headers=auth_headers,
    )
    assert set_default_response.status_code == 400
    assert "Inactive SMTP account cannot be default" in set_default_response.json()["detail"]


def test_set_default_rejects_deleted_account(client, auth_headers):
    create_response = _create_smtp_account(client, auth_headers, name="Deleted SMTP")
    account_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/smtp/accounts/{account_id}", headers=auth_headers)
    assert delete_response.status_code == 200

    set_default_response = client.post(
        f"/api/v1/smtp/accounts/{account_id}/set-default",
        headers=auth_headers,
    )
    assert set_default_response.status_code == 404


def test_soft_delete_smtp_account(client, auth_headers):
    create_response = _create_smtp_account(client, auth_headers, name="Delete Me", is_default=True)
    account_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/smtp/accounts/{account_id}", headers=auth_headers)
    assert delete_response.status_code == 200
    body = delete_response.json()
    assert body["deleted_at"] is not None
    assert body["is_active"] is False
    assert body["is_default"] is False

    get_response = client.get(f"/api/v1/smtp/accounts/{account_id}", headers=auth_headers)
    assert get_response.status_code == 404

    list_response = client.get("/api/v1/smtp/accounts", headers=auth_headers)
    assert list_response.status_code == 200
    assert list_response.json()["items"] == []


def test_set_default_makes_single_default(client, auth_headers):
    first = _create_smtp_account(client, auth_headers, name="First")
    second = _create_smtp_account(client, auth_headers, name="Second")
    second_id = second.json()["id"]

    set_default_response = client.post(
        f"/api/v1/smtp/accounts/{second_id}/set-default",
        headers=auth_headers,
    )
    assert set_default_response.status_code == 200
    assert set_default_response.json()["is_default"] is True

    first_after = client.get(f"/api/v1/smtp/accounts/{first.json()['id']}", headers=auth_headers)
    assert first_after.json()["is_default"] is False


def test_get_smtp_account_detail(client, auth_headers):
    create_response = _create_smtp_account(client, auth_headers)
    account_id = create_response.json()["id"]

    get_response = client.get(f"/api/v1/smtp/accounts/{account_id}", headers=auth_headers)
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["id"] == account_id
    assert "password" not in body
    assert body["has_password"] is True

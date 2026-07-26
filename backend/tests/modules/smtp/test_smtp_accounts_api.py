from uuid import UUID, uuid4

from app.integrations.kyrox_core.auth import create_test_token
from app.modules.email_accounts.infrastructure.persistence.models import EmailAccountSmtpConfigModel
from app.modules.smtp.infrastructure.persistence.models import SmtpAccountModel
from app.shared.secret_encryption import decrypt_secret, is_encrypted_secret


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
        "/api/v1/email-accounts",
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
    assert body["password_set"] is True
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

    list_response = client.get("/api/v1/email-accounts", headers=auth_headers)
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    defaults = [item for item in items if item["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["name"] == "Second SMTP"

    first_after = client.get(f"/api/v1/email-accounts/{first.json()['id']}", headers=auth_headers)
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
    get_response = client.get(f"/api/v1/email-accounts/{account_id}", headers=other_headers)
    assert get_response.status_code == 404


def test_list_response_does_not_include_password(client, auth_headers):
    _create_smtp_account(client, auth_headers)
    response = client.get("/api/v1/email-accounts", headers=auth_headers)
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert "password" not in item
        assert item["password_set"] is True


def test_update_password_empty_keeps_existing(client, auth_headers, db_session):
    create_response = _create_smtp_account(client, auth_headers, password="keep-me")
    account_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/email-accounts/{account_id}",
        json={"name": "Renamed SMTP", "password": ""},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Renamed SMTP"
    assert update_response.json()["password_set"] is True

    model = db_session.get(SmtpAccountModel, UUID(account_id))
    assert model is not None
    smtp_config = db_session.get(EmailAccountSmtpConfigModel, UUID(account_id))
    assert smtp_config is not None
    assert is_encrypted_secret(smtp_config.password)
    assert decrypt_secret(smtp_config.password) == "keep-me"


def test_update_password_replaces_existing(client, auth_headers, db_session):
    create_response = _create_smtp_account(client, auth_headers, password="old-secret")
    account_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/email-accounts/{account_id}",
        json={"password": "new-secret"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200

    model = db_session.get(SmtpAccountModel, UUID(account_id))
    assert model is not None
    smtp_config = db_session.get(EmailAccountSmtpConfigModel, UUID(account_id))
    assert smtp_config is not None
    assert is_encrypted_secret(smtp_config.password)
    assert decrypt_secret(smtp_config.password) == "new-secret"


def test_set_default_rejects_inactive_account(client, auth_headers):
    create_response = _create_smtp_account(client, auth_headers, name="Inactive SMTP")
    account_id = create_response.json()["id"]

    deactivate_response = client.patch(
        f"/api/v1/email-accounts/{account_id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert deactivate_response.status_code == 200

    set_default_response = client.post(
        f"/api/v1/email-accounts/{account_id}/set-default",
        headers=auth_headers,
    )
    assert set_default_response.status_code == 400
    assert "Inactive email account cannot be default" in set_default_response.json()["detail"]


def test_set_default_rejects_deleted_account(client, auth_headers):
    create_response = _create_smtp_account(client, auth_headers, name="Deleted SMTP")
    account_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/email-accounts/{account_id}", headers=auth_headers)
    assert delete_response.status_code == 200

    set_default_response = client.post(
        f"/api/v1/email-accounts/{account_id}/set-default",
        headers=auth_headers,
    )
    assert set_default_response.status_code == 404


def test_soft_delete_smtp_account(client, auth_headers):
    create_response = _create_smtp_account(client, auth_headers, name="Delete Me", is_default=True)
    account_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/email-accounts/{account_id}", headers=auth_headers)
    assert delete_response.status_code == 200
    body = delete_response.json()
    assert body["deleted_at"] is not None
    assert body["is_active"] is False
    assert body["is_default"] is False

    get_response = client.get(f"/api/v1/email-accounts/{account_id}", headers=auth_headers)
    assert get_response.status_code == 404

    list_response = client.get("/api/v1/email-accounts", headers=auth_headers)
    assert list_response.status_code == 200
    assert list_response.json()["items"] == []


def test_set_default_makes_single_default(client, auth_headers):
    first = _create_smtp_account(client, auth_headers, name="First")
    second = _create_smtp_account(client, auth_headers, name="Second")
    second_id = second.json()["id"]

    set_default_response = client.post(
        f"/api/v1/email-accounts/{second_id}/set-default",
        headers=auth_headers,
    )
    assert set_default_response.status_code == 200
    assert set_default_response.json()["is_default"] is True

    first_after = client.get(f"/api/v1/email-accounts/{first.json()['id']}", headers=auth_headers)
    assert first_after.json()["is_default"] is False


def _ensure_org_default_unique_index(db_session) -> None:
    """Mirror alembic ``uq_email_accounts_org_default`` on the test SQLite DB.

    Production Postgres enforces one default per org; in-memory create_all does not
    install this partial unique index, so set-default UniqueViolation would not
    surface without it.
    """
    from sqlalchemy import text

    db_session.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_email_accounts_org_default
            ON email_accounts (organization_id)
            WHERE deleted_at IS NULL AND is_default = 1
            """
        )
    )
    db_session.commit()


def test_set_default_respects_org_unique_default_and_is_idempotent(
    client,
    auth_headers,
    db_session,
    other_organization_id,
    user_id,
):
    _ensure_org_default_unique_index(db_session)

    first = _create_smtp_account(client, auth_headers, name="Default A")
    second = _create_smtp_account(client, auth_headers, name="Candidate B")
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["is_default"] is True
    assert second.json()["is_default"] is False

    first_id = first.json()["id"]
    second_id = second.json()["id"]

    set_default_response = client.post(
        f"/api/v1/email-accounts/{second_id}/set-default",
        headers=auth_headers,
    )
    assert set_default_response.status_code == 200, set_default_response.text
    assert set_default_response.json()["is_default"] is True

    first_after = client.get(f"/api/v1/email-accounts/{first_id}", headers=auth_headers)
    second_after = client.get(f"/api/v1/email-accounts/{second_id}", headers=auth_headers)
    assert first_after.json()["is_default"] is False
    assert second_after.json()["is_default"] is True

    list_response = client.get("/api/v1/email-accounts", headers=auth_headers)
    defaults = [item for item in list_response.json()["items"] if item["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == second_id

    # Idempotent: already-default account can be set-default again.
    again = client.post(
        f"/api/v1/email-accounts/{second_id}/set-default",
        headers=auth_headers,
    )
    assert again.status_code == 200, again.text
    assert again.json()["is_default"] is True

    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    other = _create_smtp_account(client, other_headers, name="Other Org Default")
    assert other.status_code == 201
    assert other.json()["is_default"] is True

    still_second = client.get(f"/api/v1/email-accounts/{second_id}", headers=auth_headers)
    assert still_second.json()["is_default"] is True
    other_get = client.get(f"/api/v1/email-accounts/{other.json()['id']}", headers=other_headers)
    assert other_get.json()["is_default"] is True


def test_create_default_respects_org_unique_index(
    client,
    auth_headers,
    db_session,
    other_organization_id,
    user_id,
):
    _ensure_org_default_unique_index(db_session)

    first = _create_smtp_account(client, auth_headers, name="Create Default A")
    assert first.status_code == 201
    assert first.json()["is_default"] is True

    second = _create_smtp_account(
        client,
        auth_headers,
        name="Create Default B",
        is_default=True,
    )
    assert second.status_code == 201, second.text
    assert second.json()["is_default"] is True

    first_after = client.get(f"/api/v1/email-accounts/{first.json()['id']}", headers=auth_headers)
    assert first_after.json()["is_default"] is False

    listed = client.get("/api/v1/email-accounts", headers=auth_headers)
    defaults = [item for item in listed.json()["items"] if item["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == second.json()["id"]

    non_default = _create_smtp_account(
        client,
        auth_headers,
        name="Create Non Default C",
        is_default=False,
    )
    assert non_default.status_code == 201, non_default.text
    assert non_default.json()["is_default"] is False
    still_b = client.get(f"/api/v1/email-accounts/{second.json()['id']}", headers=auth_headers)
    assert still_b.json()["is_default"] is True

    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    other = _create_smtp_account(client, other_headers, name="Other Org Create Default")
    assert other.status_code == 201
    assert other.json()["is_default"] is True
    assert still_b.json()["is_default"] is True


def test_update_default_respects_org_unique_index(client, auth_headers, db_session):
    _ensure_org_default_unique_index(db_session)

    first = _create_smtp_account(client, auth_headers, name="Update Default A")
    second = _create_smtp_account(client, auth_headers, name="Update Candidate B")
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["is_default"] is True
    assert second.json()["is_default"] is False

    first_id = first.json()["id"]
    second_id = second.json()["id"]

    update_response = client.patch(
        f"/api/v1/email-accounts/{second_id}",
        json={"is_default": True},
        headers=auth_headers,
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["is_default"] is True

    first_after = client.get(f"/api/v1/email-accounts/{first_id}", headers=auth_headers)
    second_after = client.get(f"/api/v1/email-accounts/{second_id}", headers=auth_headers)
    assert first_after.json()["is_default"] is False
    assert second_after.json()["is_default"] is True

    listed = client.get("/api/v1/email-accounts", headers=auth_headers)
    defaults = [item for item in listed.json()["items"] if item["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == second_id

    keep_false = client.patch(
        f"/api/v1/email-accounts/{first_id}",
        json={"name": "Still Not Default", "is_default": False},
        headers=auth_headers,
    )
    assert keep_false.status_code == 200, keep_false.text
    assert keep_false.json()["is_default"] is False
    assert client.get(f"/api/v1/email-accounts/{second_id}", headers=auth_headers).json()[
        "is_default"
    ] is True


def test_get_smtp_account_detail(client, auth_headers):
    create_response = _create_smtp_account(client, auth_headers)
    account_id = create_response.json()["id"]

    get_response = client.get(f"/api/v1/email-accounts/{account_id}", headers=auth_headers)
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["id"] == account_id
    assert "password" not in body
    assert body["password_set"] is True

"""Default transfer when deleting or deactivating the org default email account."""

from uuid import UUID

from app.modules.email_accounts.infrastructure.persistence.models import EmailAccountModel
from app.modules.smtp.infrastructure.repositories.smtp_account_repository import (
    SqlAlchemySmtpAccountRepository,
)
from tests.modules.smtp.test_smtp_accounts_api import _create_smtp_account


def test_delete_default_transfers_to_next_active_by_name_id(client, auth_headers, db_session):
    first = _create_smtp_account(client, auth_headers, name="Alpha SMTP", is_default=True)
    second = _create_smtp_account(client, auth_headers, name="Bravo SMTP", is_default=False)
    third = _create_smtp_account(client, auth_headers, name="Charlie SMTP", is_default=False)
    assert first.status_code == 201
    assert second.status_code == 201
    assert third.status_code == 201

    first_id = first.json()["id"]
    second_id = second.json()["id"]

    delete_response = client.delete(f"/api/v1/email-accounts/{first_id}", headers=auth_headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["is_default"] is False

    listed = client.get("/api/v1/email-accounts", headers=auth_headers)
    assert listed.status_code == 200
    items = {item["id"]: item for item in listed.json()["items"]}
    assert items[second_id]["is_default"] is True
    assert items[third.json()["id"]]["is_default"] is False

    repo = SqlAlchemySmtpAccountRepository(db_session)
    default = repo.get_default_for_organization(UUID(first.json()["organization_id"]))
    assert default is not None
    assert str(default.id) == second_id


def test_deactivate_default_transfers_to_next_active(client, auth_headers):
    first = _create_smtp_account(client, auth_headers, name="Default SMTP", is_default=True)
    second = _create_smtp_account(client, auth_headers, name="Other SMTP", is_default=False)
    first_id = first.json()["id"]
    second_id = second.json()["id"]

    deactivate = client.patch(
        f"/api/v1/email-accounts/{first_id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False
    assert deactivate.json()["is_default"] is False

    second_after = client.get(f"/api/v1/email-accounts/{second_id}", headers=auth_headers)
    assert second_after.status_code == 200
    assert second_after.json()["is_default"] is True


def test_delete_last_account_succeeds_with_no_default_left(client, auth_headers, db_session, organization_id):
    created = _create_smtp_account(client, auth_headers, name="Only SMTP", is_default=True)
    account_id = created.json()["id"]

    delete_response = client.delete(f"/api/v1/email-accounts/{account_id}", headers=auth_headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted_at"] is not None

    listed = client.get("/api/v1/email-accounts", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["items"] == []

    repo = SqlAlchemySmtpAccountRepository(db_session)
    assert repo.get_default_for_organization(organization_id) is None


def test_deactivate_last_active_succeeds_with_no_default(client, auth_headers, db_session, organization_id):
    created = _create_smtp_account(client, auth_headers, name="Solo SMTP", is_default=True)
    account_id = created.json()["id"]

    deactivate = client.patch(
        f"/api/v1/email-accounts/{account_id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False
    assert deactivate.json()["is_default"] is False

    model = db_session.get(EmailAccountModel, UUID(account_id))
    assert model is not None
    assert model.is_default is False
    assert model.is_active is False

    repo = SqlAlchemySmtpAccountRepository(db_session)
    assert repo.get_default_for_organization(organization_id) is None

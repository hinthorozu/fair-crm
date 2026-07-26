"""Tests for email_accounts.max_delivery_attempts (create + update, MSO snapshot)."""

from uuid import UUID

from app.modules.email_accounts.infrastructure.persistence.models import EmailAccountModel
from app.modules.mail_send_operations.domain.value_objects import (
    MailSendSourceType,
)
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
    SqlAlchemyMailSendOperationRepository,
)
from tests.modules.smtp.test_smtp_accounts_api import _create_smtp_account, _smtp_payload


def test_create_max_delivery_attempts_1_to_5_ok(client, auth_headers):
    for value in (1, 2, 3, 4, 5):
        response = _create_smtp_account(
            client,
            auth_headers,
            name=f"SMTP attempts {value}",
            max_delivery_attempts=value,
            is_default=False,
        )
        assert response.status_code == 201, response.text
        assert response.json()["max_delivery_attempts"] == value


def test_create_max_delivery_attempts_default_is_3(client, auth_headers):
    response = _create_smtp_account(client, auth_headers, name="Default attempts")
    assert response.status_code == 201
    assert response.json()["max_delivery_attempts"] == 3


def test_create_max_delivery_attempts_0_and_6_rejected(client, auth_headers):
    for value in (0, 6):
        response = client.post(
            "/api/v1/email-accounts",
            json=_smtp_payload(name=f"Bad {value}", max_delivery_attempts=value),
            headers=auth_headers,
        )
        assert response.status_code == 422, response.text


def test_update_can_change_max_delivery_attempts(client, auth_headers, db_session):
    created = _create_smtp_account(
        client,
        auth_headers,
        name="Editable attempts",
        max_delivery_attempts=2,
    )
    assert created.status_code == 201
    account_id = created.json()["id"]
    assert created.json()["max_delivery_attempts"] == 2

    updated = client.patch(
        f"/api/v1/email-accounts/{account_id}",
        json={"name": "Renamed", "max_delivery_attempts": 5},
        headers=auth_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Renamed"
    assert updated.json()["max_delivery_attempts"] == 5

    model = db_session.get(EmailAccountModel, UUID(account_id))
    assert model is not None
    assert model.max_delivery_attempts == 5


def test_update_max_delivery_attempts_out_of_range_rejected(client, auth_headers):
    created = _create_smtp_account(
        client,
        auth_headers,
        name="Range check",
        max_delivery_attempts=3,
    )
    account_id = created.json()["id"]
    for value in (0, 6):
        response = client.patch(
            f"/api/v1/email-accounts/{account_id}",
            json={"max_delivery_attempts": value},
            headers=auth_headers,
        )
        assert response.status_code == 422, response.text


def test_existing_mso_snapshot_unchanged_after_account_update(client, auth_headers, db_session):
    created = _create_smtp_account(
        client,
        auth_headers,
        name="Snapshot account",
        max_delivery_attempts=2,
    )
    assert created.status_code == 201
    account_id = UUID(created.json()["id"])
    account = db_session.get(EmailAccountModel, account_id)
    assert account is not None

    repo = SqlAlchemyMailSendOperationRepository(db_session)
    existing = repo.create(
        CreateMailSendOperationParams(
            organization_id=account.organization_id,
            source_type=MailSendSourceType.SMTP_TEST,
            recipient_email="snapshot@example.com",
            subject="Existing snapshot",
            body_text="body",
            email_account_id=account_id,
            max_retry_count=2,
        )
    )
    db_session.commit()
    assert existing.max_retry_count == 2

    updated = client.patch(
        f"/api/v1/email-accounts/{account_id}",
        json={"max_delivery_attempts": 5},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["max_delivery_attempts"] == 5

    loaded = repo.get_by_id(existing.organization_id, existing.id)
    assert loaded is not None
    assert loaded.max_retry_count == 2

    db_session.refresh(account)
    assert account.max_delivery_attempts == 5

    queued = repo.create(
        CreateMailSendOperationParams(
            organization_id=account.organization_id,
            source_type=MailSendSourceType.SMTP_TEST,
            recipient_email="new@example.com",
            subject="New snapshot",
            body_text="body",
            email_account_id=account_id,
            max_retry_count=account.max_delivery_attempts,
        )
    )
    db_session.commit()
    assert queued.max_retry_count == 5


def test_model_default_max_delivery_attempts_is_3(db_session, organization_id):
    from datetime import UTC, datetime
    from uuid import uuid4

    now = datetime.now(tz=UTC)
    model = EmailAccountModel(
        id=uuid4(),
        organization_id=organization_id,
        name="ORM default",
        account_type="smtp",
        from_email="noreply@example.com",
        is_default=False,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(model)
    db_session.flush()
    db_session.refresh(model)
    assert model.max_delivery_attempts == 3

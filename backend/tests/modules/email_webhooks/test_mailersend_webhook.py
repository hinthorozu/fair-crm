"""MailerSend email webhook integration tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.activities.domain.value_objects import ActivitySource
from app.modules.activities.infrastructure.persistence.models import ActivityModel
from app.modules.contacts.domain.entities import Contact
from app.modules.contacts.infrastructure.persistence.models import ContactModel
from app.modules.contacts.infrastructure.repositories.contact_repository import (
    SqlAlchemyContactRepository,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountProviderConfigModel,
)
from app.modules.email_delivery.application.provider_status_policy import (
    apply_provider_status_transition,
    should_update_provider_status,
)
from app.modules.email_webhooks.application.mailersend_signature import (
    MAILERSEND_WEBHOOK_TEST_SIGNING_SECRET,
    compute_mailersend_signature,
)
from app.modules.mail_send_operations.domain.value_objects import (
    MailSendOperationStatus,
    MailSendSourceType,
)
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
    SqlAlchemyMailSendOperationRepository,
)
from app.shared.secret_encryption import encrypt_secret
from tests.conftest_customer_helpers import create_test_customer

WEBHOOK_SECRET = "whsec_test_signing_secret_abc123"


def _sign(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return compute_mailersend_signature(raw_body=body, signing_secret=secret)


def _create_mailersend_account(
    db_session,
    organization_id,
    *,
    is_active: bool = True,
    webhook_secret: str | None = WEBHOOK_SECRET,
) -> UUID:
    now = datetime.now(tz=UTC)
    account_id = uuid4()
    db_session.add(
        EmailAccountModel(
            id=account_id,
            organization_id=organization_id,
            name="MailerSend Webhook Test",
            account_type="provider",
            provider_key="mailersend",
            from_email="noreply@example.com",
            from_name="FAIR CRM",
            is_default=False,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            max_delivery_attempts=3,
        )
    )
    config = {
        "api_token": encrypt_secret("ms-token"),
        "from_email": "noreply@example.com",
        "from_name": "FAIR CRM",
    }
    if webhook_secret:
        config["webhook_signing_secret"] = encrypt_secret(webhook_secret)
    db_session.add(
        EmailAccountProviderConfigModel(
            email_account_id=account_id,
            provider_key="mailersend",
            config_json=json.dumps(config),
            error_policy_json="{}",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.flush()
    return account_id


def _create_sent_mso(
    db_session,
    organization_id,
    email_account_id: UUID,
    *,
    message_id: str,
    provider_status: str = "accepted",
    recipient_email: str = "recipient@example.com",
    customer_id: UUID | None = None,
    metadata_json: dict | None = None,
) -> MailSendOperationModel:
    repo = SqlAlchemyMailSendOperationRepository(db_session)
    record = repo.create(
        CreateMailSendOperationParams(
            organization_id=organization_id,
            source_type=MailSendSourceType.FAIR_BULK_EMAIL,
            recipient_email=recipient_email,
            subject="Webhook test",
            body_text="Body",
            email_account_id=email_account_id,
            customer_id=customer_id,
            metadata_json=metadata_json,
        )
    )
    repo.mark_sent(
        organization_id,
        record.id,
        external_message_id=message_id,
        provider_status=provider_status,
    )
    return (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.id == record.id)
        .one()
    )


def _activity_payload(event_type: str, message_id: str, email: str = "recipient@example.com") -> dict:
    short = event_type.split(".", 1)[-1]
    return {
        "type": event_type,
        "created_at": "2025-08-05T21:23:54.000000Z",
        "data": {
            "id": "6892766a5b66e2daf3dc9155",
            "domain_id": "yv69oxl5kl785kw2",
            "message_id": message_id,
            "email_id": "6892766a8d52ba62543d5e71",
            "type": short,
            "subject": "Test email",
            "email": email,
            "tags": [],
            "meta": [],
        },
    }


def _post_webhook(client, account_id: UUID, payload: dict, *, secret: str | None = WEBHOOK_SECRET):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {}
    if secret is not None:
        headers["Signature"] = _sign(body, secret)
    return client.post(
        f"/api/v1/webhooks/email/mailersend/{account_id}",
        content=body,
        headers=headers,
    )


def _create_contact(db_session, organization_id, customer_id: UUID, email: str) -> Contact:
    now = datetime.now(tz=UTC)
    contact = Contact.create(
        organization_id=organization_id,
        customer_id=customer_id,
        first_name="Webhook",
        last_name="Contact",
        email=email,
        email_allowed=True,
        now=now,
    )
    return SqlAlchemyContactRepository(db_session).add(contact)


# --- Policy unit checks ---


def test_provider_status_policy_progression_and_no_regression():
    assert apply_provider_status_transition("accepted", "sent") == "sent"
    assert apply_provider_status_transition("sent", "delivered") == "delivered"
    assert apply_provider_status_transition("delivered", "opened") == "opened"
    assert apply_provider_status_transition("opened", "clicked") == "clicked"
    assert apply_provider_status_transition("clicked", "opened") is None
    assert apply_provider_status_transition("clicked", "delivered") is None
    assert apply_provider_status_transition("opened", "delivered") is None
    assert apply_provider_status_transition("delivered", "sent") is None
    assert apply_provider_status_transition("deferred", "delivered") == "delivered"
    assert apply_provider_status_transition("deferred", "soft_bounced") == "soft_bounced"
    assert apply_provider_status_transition("soft_bounced", "delivered") == "delivered"
    assert apply_provider_status_transition(None, "hard_bounced") == "hard_bounced"
    assert apply_provider_status_transition("hard_bounced", "sent") is None
    assert apply_provider_status_transition("unsubscribed", "opened") is None
    assert apply_provider_status_transition("spam_complaint", "delivered") is None
    assert not should_update_provider_status("clicked", "opened")


def test_webhook_test_valid_signature_no_side_effects(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    message_id = "msg-test-ping"
    mso = _create_sent_mso(db_session, organization_id, account_id, message_id=message_id)
    db_session.commit()

    payload = {
        "type": "webhook.test",
        "message": "This is a ping test message",
        "created_at": "2026-03-27T07:24:20.577080Z",
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    response = client.post(
        f"/api/v1/webhooks/email/mailersend/{account_id}",
        content=body,
        headers={"Signature": _sign(body, MAILERSEND_WEBHOOK_TEST_SIGNING_SECRET)},
    )
    assert response.status_code == 200
    db_session.refresh(mso)
    assert mso.provider_status == "accepted"
    assert db_session.query(ActivityModel).count() == 0


def test_invalid_signature_rejected_no_db_change(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    message_id = "msg-invalid-sig"
    mso = _create_sent_mso(db_session, organization_id, account_id, message_id=message_id)
    db_session.commit()

    response = _post_webhook(
        client,
        account_id,
        _activity_payload("activity.sent", message_id),
        secret="wrong-secret",
    )
    assert response.status_code == 401
    db_session.refresh(mso)
    assert mso.provider_status == "accepted"


def test_missing_signing_secret_returns_503(client, db_session, organization_id):
    account_id = _create_mailersend_account(
        db_session, organization_id, webhook_secret=None
    )
    message_id = "msg-no-secret"
    _create_sent_mso(db_session, organization_id, account_id, message_id=message_id)
    db_session.commit()

    response = _post_webhook(
        client,
        account_id,
        _activity_payload("activity.sent", message_id),
        secret="anything",
    )
    assert response.status_code == 503


def test_activity_progression_accepted_to_clicked(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    message_id = "msg-progress"
    mso = _create_sent_mso(db_session, organization_id, account_id, message_id=message_id)
    db_session.commit()

    for event, expected in [
        ("activity.sent", "sent"),
        ("activity.delivered", "delivered"),
        ("activity.opened", "opened"),
        ("activity.opened_unique", "opened"),
        ("activity.clicked", "clicked"),
        ("activity.clicked_unique", "clicked"),
    ]:
        response = _post_webhook(client, account_id, _activity_payload(event, message_id))
        assert response.status_code == 200
        db_session.refresh(mso)
        assert mso.provider_status == expected
        assert mso.status == MailSendOperationStatus.SENT


def test_out_of_order_opened_after_clicked_stays_clicked(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    message_id = "msg-ooo-click"
    mso = _create_sent_mso(
        db_session, organization_id, account_id, message_id=message_id, provider_status="clicked"
    )
    db_session.commit()

    response = _post_webhook(client, account_id, _activity_payload("activity.opened", message_id))
    assert response.status_code == 200
    db_session.refresh(mso)
    assert mso.provider_status == "clicked"


def test_out_of_order_delivered_after_opened_stays_opened(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    message_id = "msg-ooo-open"
    mso = _create_sent_mso(
        db_session, organization_id, account_id, message_id=message_id, provider_status="opened"
    )
    db_session.commit()

    response = _post_webhook(client, account_id, _activity_payload("activity.delivered", message_id))
    assert response.status_code == 200
    db_session.refresh(mso)
    assert mso.provider_status == "opened"


def test_deferred_then_delivered(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    message_id = "msg-deferred"
    mso = _create_sent_mso(
        db_session, organization_id, account_id, message_id=message_id, provider_status="deferred"
    )
    db_session.commit()
    response = _post_webhook(client, account_id, _activity_payload("activity.delivered", message_id))
    assert response.status_code == 200
    db_session.refresh(mso)
    assert mso.provider_status == "delivered"


def test_soft_bounced_then_delivered(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    message_id = "msg-soft"
    mso = _create_sent_mso(
        db_session,
        organization_id,
        account_id,
        message_id=message_id,
        provider_status="soft_bounced",
    )
    db_session.commit()
    response = _post_webhook(client, account_id, _activity_payload("activity.delivered", message_id))
    assert response.status_code == 200
    db_session.refresh(mso)
    assert mso.provider_status == "delivered"


def test_hard_bounced(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    message_id = "msg-hard"
    mso = _create_sent_mso(db_session, organization_id, account_id, message_id=message_id)
    db_session.commit()
    response = _post_webhook(
        client, account_id, _activity_payload("activity.hard_bounced", message_id)
    )
    assert response.status_code == 200
    db_session.refresh(mso)
    assert mso.provider_status == "hard_bounced"
    assert mso.status == MailSendOperationStatus.SENT


def test_unsubscribed_contact(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    customer = create_test_customer(
        db_session, organization_id, display_name="Co", email="info@co.com"
    )
    contact = _create_contact(db_session, organization_id, customer.id, "blocked@co.com")
    message_id = "msg-unsub-contact"
    mso = _create_sent_mso(
        db_session,
        organization_id,
        account_id,
        message_id=message_id,
        recipient_email="blocked@co.com",
        customer_id=customer.id,
        metadata_json={
            "contact_id": str(contact.id),
            "recipient_source": "contact",
        },
    )
    db_session.commit()

    response = _post_webhook(
        client,
        account_id,
        _activity_payload("activity.unsubscribed", message_id, email="blocked@co.com"),
    )
    assert response.status_code == 200

    db_session.expire_all()
    contact_row = db_session.get(ContactModel, contact.id)
    customer_row = db_session.get(CustomerModel, customer.id)
    db_session.refresh(mso)
    assert contact_row is not None and contact_row.email_allowed is False
    assert customer_row is not None and customer_row.email_allowed is True
    assert mso.provider_status == "unsubscribed"
    assert mso.status == MailSendOperationStatus.SENT

    activities = (
        db_session.query(ActivityModel)
        .filter(ActivityModel.customer_id == customer.id)
        .all()
    )
    assert len(activities) == 1
    assert activities[0].source == ActivitySource.EMAIL_AUTOMATION
    assert activities[0].contact_id == contact.id
    assert "unsubscribe" in (activities[0].description or "").lower()


def test_unsubscribed_customer(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    customer = create_test_customer(
        db_session, organization_id, display_name="Cust", email="cust@example.com"
    )
    message_id = "msg-unsub-customer"
    _create_sent_mso(
        db_session,
        organization_id,
        account_id,
        message_id=message_id,
        recipient_email="cust@example.com",
        customer_id=customer.id,
        metadata_json={"recipient_source": "customer"},
    )
    db_session.commit()

    response = _post_webhook(
        client,
        account_id,
        _activity_payload("activity.unsubscribed", message_id, email="cust@example.com"),
    )
    assert response.status_code == 200
    db_session.expire_all()
    customer_row = db_session.get(CustomerModel, customer.id)
    assert customer_row is not None and customer_row.email_allowed is False
    assert db_session.query(ActivityModel).filter(ActivityModel.customer_id == customer.id).count() == 1


def test_spam_complaint_contact(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    customer = create_test_customer(
        db_session, organization_id, display_name="Spam Co", email="info@spam.com"
    )
    contact = _create_contact(db_session, organization_id, customer.id, "spam@spam.com")
    message_id = "msg-spam-contact"
    _create_sent_mso(
        db_session,
        organization_id,
        account_id,
        message_id=message_id,
        recipient_email="spam@spam.com",
        customer_id=customer.id,
        metadata_json={"contact_id": str(contact.id), "recipient_source": "contact"},
    )
    db_session.commit()

    response = _post_webhook(
        client,
        account_id,
        _activity_payload("activity.spam_complaint", message_id, email="spam@spam.com"),
    )
    assert response.status_code == 200
    db_session.expire_all()
    contact_row = db_session.get(ContactModel, contact.id)
    customer_row = db_session.get(CustomerModel, customer.id)
    assert contact_row is not None and contact_row.email_allowed is False
    assert customer_row is not None and customer_row.email_allowed is True
    activity = db_session.query(ActivityModel).one()
    assert "spam complaint" in (activity.description or "").lower()


def test_spam_complaint_customer(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    customer = create_test_customer(
        db_session, organization_id, display_name="Spam Cust", email="custspam@example.com"
    )
    message_id = "msg-spam-customer"
    _create_sent_mso(
        db_session,
        organization_id,
        account_id,
        message_id=message_id,
        recipient_email="custspam@example.com",
        customer_id=customer.id,
        metadata_json={"recipient_source": "customer"},
    )
    db_session.commit()

    response = _post_webhook(
        client,
        account_id,
        _activity_payload("activity.spam_complaint", message_id, email="custspam@example.com"),
    )
    assert response.status_code == 200
    db_session.expire_all()
    customer_row = db_session.get(CustomerModel, customer.id)
    assert customer_row is not None and customer_row.email_allowed is False
    assert db_session.query(ActivityModel).count() == 1


def test_duplicate_unsubscribe_no_duplicate_activity(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    customer = create_test_customer(
        db_session, organization_id, display_name="Dup Unsub", email="dup@example.com"
    )
    message_id = "msg-dup-unsub"
    _create_sent_mso(
        db_session,
        organization_id,
        account_id,
        message_id=message_id,
        recipient_email="dup@example.com",
        customer_id=customer.id,
        metadata_json={"recipient_source": "customer"},
    )
    db_session.commit()

    payload = _activity_payload("activity.unsubscribed", message_id, email="dup@example.com")
    assert _post_webhook(client, account_id, payload).status_code == 200
    assert _post_webhook(client, account_id, payload).status_code == 200
    db_session.expire_all()
    customer_row = db_session.get(CustomerModel, customer.id)
    assert customer_row is not None and customer_row.email_allowed is False
    assert db_session.query(ActivityModel).count() == 1


def test_duplicate_spam_no_duplicate_activity(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    customer = create_test_customer(
        db_session, organization_id, display_name="Dup Spam", email="dupspam@example.com"
    )
    message_id = "msg-dup-spam"
    _create_sent_mso(
        db_session,
        organization_id,
        account_id,
        message_id=message_id,
        recipient_email="dupspam@example.com",
        customer_id=customer.id,
        metadata_json={"recipient_source": "customer"},
    )
    db_session.commit()

    payload = _activity_payload("activity.spam_complaint", message_id, email="dupspam@example.com")
    assert _post_webhook(client, account_id, payload).status_code == 200
    assert _post_webhook(client, account_id, payload).status_code == 200
    assert db_session.query(ActivityModel).count() == 1


def test_unknown_message_id_2xx_no_side_effect(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    db_session.commit()
    response = _post_webhook(
        client, account_id, _activity_payload("activity.delivered", "unknown-msg-id")
    )
    assert response.status_code == 200
    assert response.json()["outcome"] == "ignored"
    assert db_session.query(ActivityModel).count() == 0


def test_unsupported_event_2xx_ignore(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    message_id = "msg-unsupported"
    mso = _create_sent_mso(db_session, organization_id, account_id, message_id=message_id)
    db_session.commit()

    response = _post_webhook(
        client,
        account_id,
        _activity_payload("activity.survey_opened", message_id),
    )
    assert response.status_code == 200
    assert response.json()["outcome"] == "ignored"
    db_session.refresh(mso)
    assert mso.provider_status == "accepted"


def test_inactive_account_still_processes_webhook(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id, is_active=False)
    message_id = "msg-inactive"
    mso = _create_sent_mso(db_session, organization_id, account_id, message_id=message_id)
    db_session.commit()

    response = _post_webhook(client, account_id, _activity_payload("activity.delivered", message_id))
    assert response.status_code == 200
    db_session.refresh(mso)
    assert mso.provider_status == "delivered"


def test_provider_status_does_not_change_mso_pipeline_status(client, db_session, organization_id):
    account_id = _create_mailersend_account(db_session, organization_id)
    message_id = "msg-pipeline"
    mso = _create_sent_mso(db_session, organization_id, account_id, message_id=message_id)
    db_session.commit()
    assert mso.status == MailSendOperationStatus.SENT

    for event in ("activity.sent", "activity.delivered", "activity.opened", "activity.clicked"):
        assert _post_webhook(client, account_id, _activity_payload(event, message_id)).status_code == 200
        db_session.refresh(mso)
        assert mso.status == MailSendOperationStatus.SENT


def test_provider_definition_includes_webhook_signing_secret(client, auth_headers):
    response = client.get("/api/v1/email-accounts/providers", headers=auth_headers)
    assert response.status_code == 200
    mailersend = next(
        item for item in response.json()["items"] if item["provider_key"] == "mailersend"
    )
    field_keys = {field["key"] for field in mailersend["fields"]}
    assert "webhook_signing_secret" in field_keys
    secret_field = next(f for f in mailersend["fields"] if f["key"] == "webhook_signing_secret")
    assert secret_field["secret"] is True
    assert secret_field["required"] is False

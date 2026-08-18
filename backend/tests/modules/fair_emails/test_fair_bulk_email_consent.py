"""Fair bulk email consent integration tests."""

from unittest.mock import patch
from uuid import UUID

from app.modules.contacts.infrastructure.persistence.models import ContactModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.mail_send_operations.domain.value_objects import MailSendOperationStatus
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from tests.conftest_customer_helpers import create_test_customer
from tests.modules.fair_emails.test_fair_bulk_email_api import (
    _create_contact,
    _create_fair,
    _create_participation,
    _create_smtp,
    _create_template,
    _setup_fair_with_recipients,
)


@patch("app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send")
def test_bulk_send_skips_customer_with_email_consent_disabled(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
):
    data = _setup_fair_with_recipients(client, auth_headers, db_session, organization_id)
    customer = db_session.query(CustomerModel).filter(CustomerModel.id == UUID(data["customer_id"])).one()
    customer.email_allowed = False
    db_session.commit()

    response = client.post(
        f"/api/v1/fairs/{data['fair_id']}/bulk-email/send",
        json={
            "template_id": data["template_id"],
            "recipient_options": {"include_customer_emails": True, "include_contact_emails": True},
        },
        headers=auth_headers,
    )
    assert response.status_code == 400


@patch("app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send")
def test_bulk_send_excludes_contact_consent_from_mso(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
):
    fair_id = _create_fair(client, auth_headers)
    customer = create_test_customer(
        db_session,
        organization_id,
        display_name="Consent Mixed Co",
        email="info@consent.com",
    )
    db_session.commit()
    contact_id = _create_contact(client, auth_headers, str(customer.id), email="blocked@consent.com")
    _create_participation(client, auth_headers, fair_id, str(customer.id), primary_contact_id=contact_id)
    template_id = _create_template(client, auth_headers, key=f"consent_{fair_id[:8]}")
    _create_smtp(client, auth_headers)

    contact = db_session.query(ContactModel).filter(ContactModel.id == UUID(contact_id)).one()
    contact.email_allowed = False
    db_session.commit()

    preview = client.post(
        f"/api/v1/fairs/{fair_id}/bulk-email/preview-recipients",
        json={"recipient_options": {"include_customer_emails": True, "include_contact_emails": True}},
        headers=auth_headers,
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["contact_consent_skipped_count"] >= 1
    blocked_rows = [
        row
        for row in body["recipients"]
        if row["status"] == "skip" and row["skip_reason"] == "contact_email_consent"
    ]
    assert any(row["email"] == "blocked@consent.com" for row in blocked_rows)
    will_send = [row for row in body["recipients"] if row["status"] == "will_send"]
    assert any(row["email"] == "info@consent.com" for row in will_send)

    response = client.post(
        f"/api/v1/fairs/{fair_id}/bulk-email/send",
        json={
            "template_id": template_id,
            "recipient_options": {"include_customer_emails": True, "include_contact_emails": True},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    batch_id = UUID(response.json()["batch_id"])

    operations = (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.batch_id == batch_id)
        .order_by(MailSendOperationModel.created_at.asc())
        .all()
    )
    statuses = {item.status for item in operations}
    assert statuses == {MailSendOperationStatus.QUEUED}
    skipped = [item for item in operations if item.status == MailSendOperationStatus.SKIPPED]
    assert skipped == []
    assert all(item.recipient_email != "blocked@consent.com" for item in operations)
    mock_send.assert_not_called()


@patch("app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send")
def test_customer_consent_blocks_contact_even_when_contact_allowed(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
):
    fair_id = _create_fair(client, auth_headers)
    customer = create_test_customer(
        db_session,
        organization_id,
        display_name="Customer Block Co",
        email="info@block.com",
    )
    db_session.commit()
    customer_model = db_session.query(CustomerModel).filter(CustomerModel.id == customer.id).one()
    customer_model.email_allowed = False
    db_session.commit()
    contact_id = _create_contact(client, auth_headers, str(customer.id), email="open@block.com")
    _create_participation(client, auth_headers, fair_id, str(customer.id), primary_contact_id=contact_id)
    template_id = _create_template(client, auth_headers, key=f"cblock_{fair_id[:8]}")
    _create_smtp(client, auth_headers)

    contact = db_session.query(ContactModel).filter(ContactModel.id == UUID(contact_id)).one()
    contact.email_allowed = True
    db_session.commit()

    preview = client.post(
        f"/api/v1/fairs/{fair_id}/bulk-email/preview-recipients",
        json={"recipient_options": {"include_customer_emails": True, "include_contact_emails": True}},
        headers=auth_headers,
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["customer_consent_skipped_count"] >= 1
    assert body["deduped_recipient_count"] == 0
    assert all(row["status"] == "skip" for row in body["recipients"])
    assert all(row["skip_reason"] == "customer_email_consent" for row in body["recipients"])

    response = client.post(
        f"/api/v1/fairs/{fair_id}/bulk-email/send",
        json={
            "template_id": template_id,
            "recipient_options": {"include_customer_emails": True, "include_contact_emails": True},
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    mock_send.assert_not_called()

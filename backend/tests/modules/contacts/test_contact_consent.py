"""Contact email/SMS consent field tests."""

from tests.conftest_customer_helpers import create_test_customer
from tests.modules.fair_emails.test_fair_bulk_email_api import _create_contact


def test_contact_defaults_email_and_sms_allowed(client, auth_headers, db_session, organization_id):
    customer = create_test_customer(db_session, organization_id, display_name="Contact Consent Co")
    db_session.commit()

    response = client.post(
        "/api/v1/contacts",
        json={
            "customer_id": str(customer.id),
            "first_name": "Ali",
            "last_name": "Veli",
            "email": "ali@example.com",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email_allowed"] is True
    assert data["sms_allowed"] is True


def test_contact_create_with_consent_disabled(client, auth_headers, db_session, organization_id):
    customer = create_test_customer(db_session, organization_id, display_name="Contact No Email Co")
    db_session.commit()

    response = client.post(
        "/api/v1/contacts",
        json={
            "customer_id": str(customer.id),
            "first_name": "Ayşe",
            "last_name": "Yılmaz",
            "email": "ayse@example.com",
            "email_allowed": False,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email_allowed"] is False
    assert data["email_unsubscribed_at"] is not None


def test_contact_update_sms_allowed(client, auth_headers, db_session, organization_id):
    customer = create_test_customer(db_session, organization_id, display_name="SMS Consent Co")
    db_session.commit()
    contact_id = _create_contact(client, auth_headers, str(customer.id), email="sms@example.com")

    response = client.patch(
        f"/api/v1/contacts/{contact_id}",
        json={"sms_allowed": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["sms_allowed"] is False
    assert response.json()["sms_unsubscribed_at"] is not None

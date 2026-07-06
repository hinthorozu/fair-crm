"""Customer email/SMS consent field tests."""

from tests.conftest_customer_helpers import create_test_customer


def test_customer_defaults_email_and_sms_allowed(client, auth_headers, db_session, organization_id):
    response = client.post(
        "/api/v1/customers",
        json={"display_name": "Consent Default Co"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email_allowed"] is True
    assert data["sms_allowed"] is True
    assert data["email_unsubscribed_at"] is None
    assert data["sms_unsubscribed_at"] is None


def test_customer_create_with_consent_disabled(client, auth_headers):
    response = client.post(
        "/api/v1/customers",
        json={
            "display_name": "No Email Co",
            "email_allowed": False,
            "sms_allowed": False,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email_allowed"] is False
    assert data["sms_allowed"] is False
    assert data["email_unsubscribed_at"] is not None
    assert data["sms_unsubscribed_at"] is not None


def test_customer_update_consent_fields(client, auth_headers, db_session, organization_id):
    customer = create_test_customer(db_session, organization_id, display_name="Update Consent Co")
    db_session.commit()

    response = client.patch(
        f"/api/v1/customers/{customer.id}",
        json={"email_allowed": False, "sms_allowed": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email_allowed"] is False
    assert data["sms_allowed"] is True
    assert data["email_unsubscribed_at"] is not None

    response = client.patch(
        f"/api/v1/customers/{customer.id}",
        json={"email_allowed": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email_allowed"] is True
    assert data["email_unsubscribed_at"] is None


def test_existing_customer_migration_defaults_true(db_session, organization_id):
    from app.modules.customers.infrastructure.persistence.models import CustomerModel

    customer = create_test_customer(db_session, organization_id, display_name="Legacy Customer")
    db_session.commit()
    db_session.expire_all()

    model = db_session.query(CustomerModel).filter(CustomerModel.id == customer.id).one()
    assert model.email_allowed is True
    assert model.sms_allowed is True

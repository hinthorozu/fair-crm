"""GET /customers/{id} communication collection scenarios."""

from uuid import UUID

from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerPhoneModel,
    CustomerWebsiteModel,
)


def test_get_customer_without_communication_rows_returns_empty(client, auth_headers, db_session):
    """Communication data lives only in child tables after column removal."""
    create_response = client.post(
        "/api/v1/customers",
        json={
            "display_name": "Legacy Scalar Co",
            "phone": "0212 555 0300",
            "email": "legacy@example.com",
            "website": "https://legacy.example.com",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    customer_id = UUID(create_response.json()["id"])

    db_session.query(CustomerPhoneModel).filter(
        CustomerPhoneModel.customer_id == customer_id,
    ).delete(synchronize_session=False)
    db_session.query(CustomerEmailModel).filter(
        CustomerEmailModel.customer_id == customer_id,
    ).delete(synchronize_session=False)
    db_session.query(CustomerWebsiteModel).filter(
        CustomerWebsiteModel.customer_id == customer_id,
    ).delete(synchronize_session=False)
    db_session.flush()

    get_response = client.get(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["phones"] == []
    assert body["emails"] == []
    assert body["websites"] == []
    assert body["phone"] is None
    assert body["email"] is None
    assert body["website"] is None


def test_get_customer_with_single_communication_rows(client, auth_headers):
    create_response = client.post(
        "/api/v1/customers",
        json={
            "display_name": "Single Comm Co",
            "phone": "0532 555 0400",
            "email": "single@example.com",
            "website": "https://single.example.com",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    created = create_response.json()
    customer_id = created["id"]

    get_response = client.get(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert get_response.status_code == 200
    body = get_response.json()
    assert len(body["phones"]) == 1
    assert body["phones"][0]["phone"] == "905325550400"
    assert body["phones"][0]["is_primary"] is True
    assert len(body["emails"]) == 1
    assert body["emails"][0]["email"] == "single@example.com"
    assert len(body["websites"]) == 1
    assert body["websites"][0]["website"] == "single.example.com"


def test_get_customer_with_multiple_communication_rows(client, auth_headers):
    create_response = client.post(
        "/api/v1/customers",
        json={
            "display_name": "Multi Comm Co",
            "phones": [
                {"phone": "0212 555 0501", "is_primary": False},
                {"phone": "0532 555 0502", "is_primary": True},
            ],
            "emails": [
                {"email": "info@multi.example.com", "is_primary": True},
                {"email": "export@multi.example.com", "is_primary": False},
            ],
            "websites": [
                {"website": "https://multi.example.com", "is_primary": True},
                {"website": "https://multi.com.tr", "is_primary": False},
            ],
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    customer_id = create_response.json()["id"]

    get_response = client.get(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert get_response.status_code == 200
    body = get_response.json()
    assert len(body["phones"]) == 2
    assert body["phones"][0]["is_primary"] is True
    assert body["phones"][0]["phone"] == "905325550502"
    assert len(body["emails"]) == 2
    assert body["emails"][0]["email"] == "info@multi.example.com"
    assert len(body["websites"]) == 2
    assert body["websites"][0]["website"] == "multi.example.com"

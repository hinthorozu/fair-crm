def test_list_customers_uses_primary_communication_values(client, auth_headers):
    create_response = client.post(
        "/api/v1/customers",
        json={
            "display_name": "List Comm Co",
            "phones": [
                {"phone": "0212 555 0601", "is_primary": False},
                {"phone": "0532 555 0602", "is_primary": True},
            ],
            "emails": [
                {"email": "info@list.example.com", "is_primary": True},
                {"email": "export@list.example.com", "is_primary": False},
                {"email": "sales@list.example.com", "is_primary": False},
            ],
            "websites": [
                {"website": "https://secondary.list.example.com", "is_primary": False},
                {"website": "https://primary.list.example.com", "is_primary": True},
            ],
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    customer_id = create_response.json()["id"]

    list_response = client.get("/api/v1/customers", headers=auth_headers)
    assert list_response.status_code == 200
    item = next(row for row in list_response.json()["items"] if row["id"] == customer_id)

    assert item["phone"] == "905325550602"
    assert item["phone_extra_count"] == 1
    assert item["email"] == "info@list.example.com"
    assert item["email_extra_count"] == 2
    assert item["website"] == "primary.list.example.com"
    assert item["website_extra_count"] == 1
    assert item["phones"] == []
    assert item["emails"] == []
    assert item["websites"] == []


def test_list_customers_returns_empty_communication_when_no_child_rows(client, auth_headers, db_session):
    from uuid import UUID

    from app.modules.customers.infrastructure.persistence.communication_models import (
        CustomerEmailModel,
        CustomerPhoneModel,
        CustomerWebsiteModel,
    )

    create_response = client.post(
        "/api/v1/customers",
        json={
            "display_name": "Legacy List Co",
            "phone": "0212 555 0700",
            "email": "first@legacy.com;second@legacy.com",
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

    list_response = client.get("/api/v1/customers", headers=auth_headers)
    assert list_response.status_code == 200
    item = next(row for row in list_response.json()["items"] if row["id"] == str(customer_id))

    assert item["phone"] is None
    assert item["phone_extra_count"] == 0
    assert item["email"] is None
    assert item["email_extra_count"] == 0
    assert item["website"] is None
    assert item["website_extra_count"] == 0

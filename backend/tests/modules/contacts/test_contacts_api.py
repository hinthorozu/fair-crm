from uuid import uuid4


def _create_customer(client, auth_headers, name="Contact Test Customer"):
    response = client.post(
        "/api/v1/customers",
        json={"display_name": name, "status": "active"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_contact(client, auth_headers, customer_id, **overrides):
    payload = {
        "customer_id": customer_id,
        "first_name": "Ayşe",
        "last_name": "Demir",
        "title": "Satış Müdürü",
        "department": "Satış",
        "email": "ayse@example.com",
        "phone": "0212 555 0101",
        "is_primary": False,
        "is_active": True,
    }
    payload.update(overrides)
    return client.post("/api/v1/contacts", json=payload, headers=auth_headers)


def test_create_and_get_contact(client, auth_headers, organization_id):
    customer_id = _create_customer(client, auth_headers)

    create_response = _create_contact(client, auth_headers, customer_id)
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["first_name"] == "Ayşe"
    assert body["last_name"] == "Demir"
    assert body["full_name"] == "Ayşe Demir"
    assert body["customer_id"] == customer_id
    assert body["organization_id"] == str(organization_id)
    assert body["email"] == "ayse@example.com"

    contact_id = body["id"]
    get_response = client.get(f"/api/v1/contacts/{contact_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == contact_id


def test_list_contacts_by_customer(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "List Contacts Customer")
    _create_contact(client, auth_headers, customer_id, first_name="Mehmet", last_name="Kaya")
    _create_contact(client, auth_headers, customer_id, first_name="Zeynep", last_name="Arslan")

    list_response = client.get(
        f"/api/v1/customers/{customer_id}/contacts",
        headers=auth_headers,
    )
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_update_contact(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Update Contact Customer")
    create_response = _create_contact(client, auth_headers, customer_id)
    contact_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/contacts/{contact_id}",
        json={"title": "Genel Müdür", "department": "Yönetim"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Genel Müdür"
    assert update_response.json()["department"] == "Yönetim"


def test_delete_contact(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Delete Contact Customer")
    create_response = _create_contact(client, auth_headers, customer_id)
    contact_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/contacts/{contact_id}", headers=auth_headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted_at"] is not None
    assert delete_response.json()["is_active"] is False

    get_response = client.get(f"/api/v1/contacts/{contact_id}", headers=auth_headers)
    assert get_response.status_code == 404

    list_response = client.get(
        f"/api/v1/customers/{customer_id}/contacts",
        headers=auth_headers,
    )
    assert list_response.json()["total"] == 0


def test_contact_cannot_be_created_without_valid_customer(client, auth_headers):
    response = _create_contact(client, auth_headers, str(uuid4()))
    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"


def test_only_one_primary_contact_per_customer(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Primary Contact Customer")

    first = _create_contact(
        client,
        auth_headers,
        customer_id,
        first_name="Primary",
        last_name="One",
        is_primary=True,
    )
    assert first.status_code == 201
    first_id = first.json()["id"]

    second = _create_contact(
        client,
        auth_headers,
        customer_id,
        first_name="Primary",
        last_name="Two",
        is_primary=True,
    )
    assert second.status_code == 201
    assert second.json()["is_primary"] is True

    first_after = client.get(f"/api/v1/contacts/{first_id}", headers=auth_headers)
    assert first_after.status_code == 200
    assert first_after.json()["is_primary"] is False


def test_updating_contact_to_primary_clears_previous_primary(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Update Primary Customer")

    primary = _create_contact(
        client,
        auth_headers,
        customer_id,
        first_name="Old",
        last_name="Primary",
        is_primary=True,
    )
    primary_id = primary.json()["id"]

    secondary = _create_contact(
        client,
        auth_headers,
        customer_id,
        first_name="New",
        last_name="Primary",
        is_primary=False,
    )
    secondary_id = secondary.json()["id"]

    update_response = client.patch(
        f"/api/v1/contacts/{secondary_id}",
        json={"is_primary": True},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_primary"] is True

    old_primary = client.get(f"/api/v1/contacts/{primary_id}", headers=auth_headers)
    assert old_primary.json()["is_primary"] is False


def test_contact_create_rejected_for_archived_customer(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Archived Parent Customer")
    client.delete(f"/api/v1/customers/{customer_id}", headers=auth_headers)

    response = _create_contact(client, auth_headers, customer_id)
    assert response.status_code == 400
    assert response.json()["detail"] == "Customer is archived"


def test_contact_multi_email_normalized(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Contact Multi Email")
    response = _create_contact(
        client,
        auth_headers,
        customer_id,
        email="info@abc.com ; sales@abc.com, info@abc.com",
    )
    assert response.status_code == 201
    assert response.json()["email"] == "info@abc.com;sales@abc.com"

    contact_id = response.json()["id"]
    get_response = client.get(f"/api/v1/contacts/{contact_id}", headers=auth_headers)
    assert get_response.json()["email"] == "info@abc.com;sales@abc.com"


def test_contact_invalid_multi_email_rejected(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Contact Bad Email")
    response = _create_contact(
        client,
        auth_headers,
        customer_id,
        email="valid@abc.com;bad@@abc.com",
    )
    assert response.status_code == 400
    assert "Invalid email address: bad@@abc.com" in response.json()["detail"]

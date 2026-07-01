"""Tests for customer fair participation API."""

from datetime import UTC, datetime


def _create_customer(client, auth_headers, name="Participation Customer"):
    response = client.post(
        "/api/v1/customers",
        json={"display_name": name, "status": "active"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_fair(client, auth_headers, name="Test Fair"):
    response = client.post(
        "/api/v1/fairs",
        json={"name": name, "status": "planned"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_contact(client, auth_headers, customer_id, **overrides):
    payload = {
        "customer_id": customer_id,
        "first_name": "Ali",
        "last_name": "Veli",
        "is_primary": True,
        "is_active": True,
    }
    payload.update(overrides)
    response = client.post("/api/v1/contacts", json=payload, headers=auth_headers)
    assert response.status_code == 201
    return response.json()["id"]


def _participation_payload(customer_id, fair_id, **overrides):
    payload = {
        "customer_id": customer_id,
        "fair_id": fair_id,
        "hall": "A",
        "stand": "12",
        "participation_status": "exhibitor",
    }
    payload.update(overrides)
    return payload


def test_create_participation(client, auth_headers):
    customer_id = _create_customer(client, auth_headers)
    fair_id = _create_fair(client, auth_headers)

    response = client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(customer_id, fair_id),
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["customer_id"] == customer_id
    assert body["fair_id"] == fair_id
    assert body["hall"] == "A"
    assert body["stand"] == "12"
    assert body["participation_status"] == "exhibitor"


def test_duplicate_active_participation_rejected(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Dup Customer")
    fair_id = _create_fair(client, auth_headers, "Dup Fair")

    first = client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(customer_id, fair_id),
        headers=auth_headers,
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(customer_id, fair_id, hall="B"),
        headers=auth_headers,
    )
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"].lower()


def test_list_participations_by_customer(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "List Customer")
    fair_id = _create_fair(client, auth_headers, "List Fair")
    client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(customer_id, fair_id),
        headers=auth_headers,
    )

    response = client.get(
        f"/api/v1/customers/{customer_id}/fair-participations",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["fair_name"] == "List Fair"
    assert body["items"][0]["hall"] == "A"


def test_list_participants_by_fair(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Fair Participant Co")
    fair_id = _create_fair(client, auth_headers, "Participants Fair")
    client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(customer_id, fair_id),
        headers=auth_headers,
    )

    response = client.get(f"/api/v1/fairs/{fair_id}/participants", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["company_name"] == "Fair Participant Co"


def test_update_participation(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Update Customer")
    fair_id = _create_fair(client, auth_headers, "Update Fair")
    create = client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(customer_id, fair_id),
        headers=auth_headers,
    )
    participation_id = create.json()["id"]

    update = client.patch(
        f"/api/v1/fair-participations/{participation_id}",
        json={"hall": "C", "stand": "99", "participation_status": "visited"},
        headers=auth_headers,
    )
    assert update.status_code == 200
    assert update.json()["hall"] == "C"
    assert update.json()["stand"] == "99"
    assert update.json()["participation_status"] == "visited"


def test_soft_delete_participation(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Delete Customer")
    fair_id = _create_fair(client, auth_headers, "Delete Fair")
    create = client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(customer_id, fair_id),
        headers=auth_headers,
    )
    participation_id = create.json()["id"]

    delete = client.delete(
        f"/api/v1/fair-participations/{participation_id}",
        headers=auth_headers,
    )
    assert delete.status_code == 200
    assert delete.json()["deleted_at"] is not None
    assert delete.json()["is_active"] is False

    get = client.get(f"/api/v1/fair-participations/{participation_id}", headers=auth_headers)
    assert get.status_code == 404

    listed = client.get(
        f"/api/v1/customers/{customer_id}/fair-participations",
        headers=auth_headers,
    )
    assert listed.json()["total"] == 0


def test_recreate_after_soft_delete(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Recreate Customer")
    fair_id = _create_fair(client, auth_headers, "Recreate Fair")
    create = client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(customer_id, fair_id),
        headers=auth_headers,
    )
    participation_id = create.json()["id"]
    client.delete(f"/api/v1/fair-participations/{participation_id}", headers=auth_headers)

    recreate = client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(customer_id, fair_id, hall="New Hall"),
        headers=auth_headers,
    )
    assert recreate.status_code == 201
    assert recreate.json()["hall"] == "New Hall"


def test_primary_contact_same_customer_accepted(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Contact OK Customer")
    fair_id = _create_fair(client, auth_headers, "Contact OK Fair")
    contact_id = _create_contact(client, auth_headers, customer_id)

    response = client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(customer_id, fair_id, primary_contact_id=contact_id),
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["primary_contact_id"] == contact_id
    assert response.json()["primary_contact_name"] == "Ali Veli"


def test_primary_contact_other_customer_rejected(client, auth_headers):
    customer_a = _create_customer(client, auth_headers, "Customer A")
    customer_b = _create_customer(client, auth_headers, "Customer B")
    fair_id = _create_fair(client, auth_headers, "Mismatch Fair")
    contact_b = _create_contact(client, auth_headers, customer_b)

    response = client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(customer_a, fair_id, primary_contact_id=contact_b),
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Contact does not belong to this customer"


def test_create_rejected_for_archived_customer(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Archived Customer")
    fair_id = _create_fair(client, auth_headers, "Archived Cust Fair")
    client.delete(f"/api/v1/customers/{customer_id}", headers=auth_headers)

    response = client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(customer_id, fair_id),
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Customer is archived"


def test_create_rejected_for_archived_fair(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Active Customer")
    fair_id = _create_fair(client, auth_headers, "Archived Fair")
    client.delete(f"/api/v1/fairs/{fair_id}", headers=auth_headers)

    response = client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(customer_id, fair_id),
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Fair is archived"


def test_get_participation(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Get Customer")
    fair_id = _create_fair(client, auth_headers, "Get Fair")
    create = client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(customer_id, fair_id),
        headers=auth_headers,
    )
    participation_id = create.json()["id"]

    get = client.get(f"/api/v1/fair-participations/{participation_id}", headers=auth_headers)
    assert get.status_code == 200
    assert get.json()["id"] == participation_id

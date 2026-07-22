"""Tests for customer fair participation API."""

from tests.conftest_helpers import pagination_from


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


def _participation_payload(customer_id, fair_id, **overrides):
    payload = {
        "customer_id": customer_id,
        "fair_id": fair_id,
        "hall": "A",
        "stand": "12",
        "notes": "Salon notu",
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
    assert body["notes"] == "Salon notu"
    assert "participation_status" not in body
    assert "visited_at" not in body
    assert "primary_contact_id" not in body


def test_create_ignores_legacy_workflow_fields(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Legacy Ignore Customer")
    fair_id = _create_fair(client, auth_headers, "Legacy Ignore Fair")

    response = client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(
            customer_id,
            fair_id,
            participation_status="visited",
            visited_at="2026-01-01T10:00:00Z",
            primary_contact_id="00000000-0000-0000-0000-000000000001",
        ),
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["hall"] == "A"
    assert "participation_status" not in body
    assert "visited_at" not in body
    assert "primary_contact_id" not in body


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
    assert pagination_from(body)["totalItems"] == 1
    item = body["items"][0]
    assert item["fair_name"] == "List Fair"
    assert item["hall"] == "A"
    assert item["stand"] == "12"
    assert item["notes"] == "Salon notu"
    assert "participation_status" not in item
    assert "visited_at" not in item
    assert "primary_contact_name" not in item


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
    assert pagination_from(body)["totalItems"] == 1
    item = body["items"][0]
    assert item["company_name"] == "Fair Participant Co"
    assert item["hall"] == "A"
    assert item["stand"] == "12"
    assert item["notes"] == "Salon notu"
    assert "participation_status" not in item


def test_list_participants_by_fair_search(client, auth_headers):
    akdas_id = _create_customer(client, auth_headers, "AKDAS OUTDOOR TEST")
    other_id = _create_customer(client, auth_headers, "Other Fair Co")
    fair_id = _create_fair(client, auth_headers, "Search Fair")
    client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(akdas_id, fair_id),
        headers=auth_headers,
    )
    client.post(
        "/api/v1/fair-participations",
        json=_participation_payload(other_id, fair_id),
        headers=auth_headers,
    )

    response = client.get(
        f"/api/v1/fairs/{fair_id}/participants?search=AKDAS",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert pagination_from(body)["totalItems"] == 1
    assert body["items"][0]["company_name"] == "AKDAS OUTDOOR TEST"
    assert body["filters"]["search"] == "AKDAS"


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
        json={"hall": "C", "stand": "99", "notes": "Güncellendi"},
        headers=auth_headers,
    )
    assert update.status_code == 200
    body = update.json()
    assert body["hall"] == "C"
    assert body["stand"] == "99"
    assert body["notes"] == "Güncellendi"
    assert "participation_status" not in body


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
    assert pagination_from(listed.json())["totalItems"] == 0


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
    body = get.json()
    assert body["id"] == participation_id
    assert body["notes"] == "Salon notu"
    assert "participation_status" not in body

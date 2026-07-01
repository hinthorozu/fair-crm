from datetime import UTC, datetime
from uuid import uuid4


from tests.conftest_helpers import pagination_from


def _create_customer(client, auth_headers, name="Activity Test Customer"):
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
        "is_primary": False,
        "is_active": True,
    }
    payload.update(overrides)
    response = client.post("/api/v1/contacts", json=payload, headers=auth_headers)
    assert response.status_code == 201
    return response.json()["id"]


def _activity_payload(customer_id, **overrides):
    now = datetime.now(tz=UTC).isoformat()
    payload = {
        "customer_id": customer_id,
        "type": "call",
        "subject": "Telefon görüşmesi",
        "activity_date": now,
        "status": "open",
    }
    payload.update(overrides)
    return payload


def _create_activity(client, auth_headers, customer_id, **overrides):
    return client.post(
        "/api/v1/activities",
        json=_activity_payload(customer_id, **overrides),
        headers=auth_headers,
    )


def test_create_and_get_activity(client, auth_headers, organization_id):
    customer_id = _create_customer(client, auth_headers)

    create_response = _create_activity(client, auth_headers, customer_id)
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["subject"] == "Telefon görüşmesi"
    assert body["type"] == "call"
    assert body["status"] == "open"
    assert body["source"] == "manual"
    assert body["customer_id"] == customer_id
    assert body["organization_id"] == str(organization_id)
    assert body["contact_id"] is None

    activity_id = body["id"]
    get_response = client.get(f"/api/v1/activities/{activity_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == activity_id


def test_list_activities_by_customer(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "List Activities Customer")
    _create_activity(client, auth_headers, customer_id, subject="First")
    _create_activity(client, auth_headers, customer_id, subject="Second", type="meeting")

    list_response = client.get(
        f"/api/v1/customers/{customer_id}/activities",
        headers=auth_headers,
    )
    assert list_response.status_code == 200
    body = list_response.json()
    assert pagination_from(body)["totalItems"] == 2
    assert len(body["items"]) == 2


def test_update_activity(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Update Activity Customer")
    create_response = _create_activity(client, auth_headers, customer_id)
    activity_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/activities/{activity_id}",
        json={"subject": "Güncellenmiş konu", "status": "completed"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["subject"] == "Güncellenmiş konu"
    assert update_response.json()["status"] == "completed"


def test_delete_activity(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Delete Activity Customer")
    create_response = _create_activity(client, auth_headers, customer_id)
    activity_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/activities/{activity_id}", headers=auth_headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted_at"] is not None
    assert delete_response.json()["is_active"] is False

    get_response = client.get(f"/api/v1/activities/{activity_id}", headers=auth_headers)
    assert get_response.status_code == 404

    list_response = client.get(
        f"/api/v1/customers/{customer_id}/activities",
        headers=auth_headers,
    )
    assert pagination_from(list_response.json())["totalItems"] == 0


def test_activity_with_optional_contact(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Contact Activity Customer")
    contact_id = _create_contact(client, auth_headers, customer_id)

    response = _create_activity(
        client,
        auth_headers,
        customer_id,
        contact_id=contact_id,
    )
    assert response.status_code == 201
    assert response.json()["contact_id"] == contact_id
    assert response.json()["contact_full_name"] == "Ayşe Demir"


def test_activity_contact_must_belong_to_customer(client, auth_headers):
    customer_a = _create_customer(client, auth_headers, "Customer A")
    customer_b = _create_customer(client, auth_headers, "Customer B")
    contact_b = _create_contact(client, auth_headers, customer_b)

    response = _create_activity(
        client,
        auth_headers,
        customer_a,
        contact_id=contact_b,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Contact does not belong to this customer"


def test_activity_type_required(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Type Required Customer")
    payload = _activity_payload(customer_id)
    del payload["type"]

    response = client.post("/api/v1/activities", json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_activity_subject_required(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Subject Required Customer")

    response = _create_activity(client, auth_headers, customer_id, subject="")
    assert response.status_code == 422


def test_activity_status_required(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Status Required Customer")
    payload = _activity_payload(customer_id)
    del payload["status"]

    response = client.post("/api/v1/activities", json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_activity_source_defaults_to_manual(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Source Default Customer")
    response = _create_activity(client, auth_headers, customer_id)
    assert response.status_code == 201
    assert response.json()["source"] == "manual"


def test_activity_cannot_be_created_for_missing_customer(client, auth_headers):
    response = _create_activity(client, auth_headers, str(uuid4()))
    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"


def test_activity_create_rejected_for_archived_customer(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Archived Activity Customer")
    client.delete(f"/api/v1/customers/{customer_id}", headers=auth_headers)

    response = _create_activity(client, auth_headers, customer_id)
    assert response.status_code == 400
    assert response.json()["detail"] == "Customer is archived"

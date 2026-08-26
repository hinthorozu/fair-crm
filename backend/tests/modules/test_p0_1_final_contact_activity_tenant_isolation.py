"""TI-09 adversarial certification for contacts and activities."""


def _create_customer(client, headers, name: str) -> str:
    response = client.post(
        "/api/v1/customers",
        headers=headers,
        json={"display_name": name, "status": "active"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_contact(client, headers, customer_id: str, first_name: str) -> str:
    response = client.post(
        "/api/v1/contacts",
        headers=headers,
        json={
            "customer_id": customer_id,
            "first_name": first_name,
            "last_name": "Certification",
            "is_primary": False,
            "is_active": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_activity(client, headers, customer_id: str, subject: str) -> str:
    response = client.post(
        "/api/v1/activities",
        headers=headers,
        json={
            "customer_id": customer_id,
            "type": "call",
            "subject": subject,
            "activity_date": "2026-08-26T12:00:00+00:00",
            "status": "open",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_contact_direct_foreign_id_and_foreign_parent_fail_closed(
    client,
    auth_headers,
    other_organization_id,
):
    owner_customer_id = _create_customer(client, auth_headers, "Owner Contact Parent")
    owner_contact_id = _create_contact(client, auth_headers, owner_customer_id, "Owner")

    foreign_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    foreign_customer_id = _create_customer(
        client,
        foreign_headers,
        "Foreign Contact Parent",
    )

    foreign_read = client.get(
        f"/api/v1/contacts/{owner_contact_id}",
        headers=foreign_headers,
    )
    foreign_update = client.patch(
        f"/api/v1/contacts/{owner_contact_id}",
        headers=foreign_headers,
        json={"title": "Foreign overwrite"},
    )
    cross_parent = client.post(
        "/api/v1/contacts",
        headers=auth_headers,
        json={
            "customer_id": foreign_customer_id,
            "first_name": "Cross",
            "last_name": "Tenant",
            "is_active": True,
        },
    )

    assert foreign_read.status_code == 404, foreign_read.text
    assert foreign_update.status_code == 404, foreign_update.text
    assert cross_parent.status_code == 404, cross_parent.text

    owner_after = client.get(
        f"/api/v1/contacts/{owner_contact_id}",
        headers=auth_headers,
    )
    assert owner_after.status_code == 200, owner_after.text
    assert owner_after.json()["first_name"] == "Owner"
    assert owner_after.json()["title"] is None


def test_activity_direct_and_mixed_bulk_foreign_ids_fail_closed(
    client,
    auth_headers,
    other_organization_id,
):
    owner_customer_id = _create_customer(client, auth_headers, "Owner Activity Parent")
    owner_activity_id = _create_activity(
        client,
        auth_headers,
        owner_customer_id,
        "Owner Activity",
    )

    foreign_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    foreign_customer_id = _create_customer(
        client,
        foreign_headers,
        "Foreign Activity Parent",
    )
    foreign_activity_id = _create_activity(
        client,
        foreign_headers,
        foreign_customer_id,
        "Foreign Activity",
    )

    foreign_read = client.get(
        f"/api/v1/activities/{owner_activity_id}",
        headers=foreign_headers,
    )
    assert foreign_read.status_code == 404, foreign_read.text

    bulk = client.post(
        "/api/v1/activities/bulk-delete",
        headers=auth_headers,
        json={"activity_ids": [owner_activity_id, foreign_activity_id]},
    )
    assert bulk.status_code == 200, bulk.text
    body = bulk.json()
    assert body["deleted_count"] == 1
    assert body["not_found_count"] == 1
    assert body["deleted_ids"] == [owner_activity_id]
    assert body["not_found_ids"] == [foreign_activity_id]

    owner_after = client.get(
        f"/api/v1/activities/{owner_activity_id}",
        headers=auth_headers,
    )
    foreign_after = client.get(
        f"/api/v1/activities/{foreign_activity_id}",
        headers=foreign_headers,
    )
    assert owner_after.status_code == 404
    assert foreign_after.status_code == 200, foreign_after.text
    assert foreign_after.json()["subject"] == "Foreign Activity"

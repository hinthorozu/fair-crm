"""Adversarial tenant-isolation coverage for activity-derived customer joins."""

from uuid import UUID

from app.modules.activities.infrastructure.persistence.models import ActivityModel
from tests.conftest_helpers import pagination_from


def _create_customer(client, headers, name: str) -> str:
    response = client.post(
        "/api/v1/customers",
        headers=headers,
        json={"display_name": name, "status": "active"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_activity_list_search_does_not_follow_foreign_customer(
    client,
    auth_headers,
    db_session,
    other_organization_id,
):
    owner_customer_id = _create_customer(client, auth_headers, "Owner Activity Customer")
    created = client.post(
        "/api/v1/activities",
        headers=auth_headers,
        json={
            "customer_id": owner_customer_id,
            "type": "call",
            "subject": "Owner activity subject",
            "activity_date": "2026-08-26T06:00:00Z",
            "status": "open",
        },
    )
    assert created.status_code == 201, created.text

    other_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    foreign_customer_id = _create_customer(
        client,
        other_headers,
        "FOREIGN ACTIVITY CUSTOMER UNIQUE",
    )

    activity = db_session.get(ActivityModel, UUID(created.json()["id"]))
    assert activity is not None
    activity.customer_id = UUID(foreign_customer_id)
    db_session.commit()

    response = client.get(
        "/api/v1/activities?search=FOREIGN%20ACTIVITY%20CUSTOMER%20UNIQUE",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "FOREIGN ACTIVITY CUSTOMER UNIQUE" not in response.text
    assert pagination_from(response.json())["totalItems"] == 0

    unfiltered = client.get("/api/v1/activities", headers=auth_headers)
    assert unfiltered.status_code == 200
    item = next(row for row in unfiltered.json()["items"] if row["id"] == created.json()["id"])
    assert item["customer_name"] is None

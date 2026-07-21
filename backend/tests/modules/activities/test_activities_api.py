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


def test_delete_activity_hard_deletes_from_db(client, auth_headers, db_session):
    from uuid import UUID

    from app.modules.activities.infrastructure.persistence.models import ActivityModel

    customer_id = _create_customer(client, auth_headers, "Delete Activity Customer")
    create_response = _create_activity(client, auth_headers, customer_id)
    activity_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/activities/{activity_id}", headers=auth_headers)
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/activities/{activity_id}", headers=auth_headers)
    assert get_response.status_code == 404

    list_response = client.get(
        f"/api/v1/customers/{customer_id}/activities",
        headers=auth_headers,
    )
    assert pagination_from(list_response.json())["totalItems"] == 0

    db_session.expire_all()
    row = db_session.get(ActivityModel, UUID(activity_id))
    assert row is None


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


def test_list_all_activities(client, auth_headers):
    customer_a = _create_customer(client, auth_headers, "Central List Customer A")
    customer_b = _create_customer(client, auth_headers, "Central List Customer B")
    _create_activity(client, auth_headers, customer_a, subject="Call A")
    _create_activity(client, auth_headers, customer_b, subject="Meeting B", type="meeting")

    response = client.get("/api/v1/activities", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert pagination_from(body)["totalItems"] >= 2
    subjects = {item["subject"] for item in body["items"]}
    assert "Call A" in subjects
    assert "Meeting B" in subjects
    assert all(item.get("customer_name") for item in body["items"] if item["subject"] in subjects)


def test_list_activities_filter_by_customer(client, auth_headers):
    customer_a = _create_customer(client, auth_headers, "Filter Customer A")
    customer_b = _create_customer(client, auth_headers, "Filter Customer B")
    _create_activity(client, auth_headers, customer_a, subject="Only A")
    _create_activity(client, auth_headers, customer_b, subject="Only B")

    response = client.get(
        f"/api/v1/activities?customerId={customer_a}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert pagination_from(body)["totalItems"] == 1
    assert body["items"][0]["subject"] == "Only A"
    assert body["items"][0]["customer_id"] == customer_a


def test_list_activities_filter_by_type(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Type Filter Customer")
    _create_activity(client, auth_headers, customer_id, subject="Call", type="call")
    _create_activity(client, auth_headers, customer_id, subject="Meet", type="meeting")

    response = client.get(
        "/api/v1/activities?activityType=meeting",
        headers=auth_headers,
    )
    assert response.status_code == 200
    items = [i for i in response.json()["items"] if i["customer_id"] == customer_id]
    assert len(items) == 1
    assert items[0]["type"] == "meeting"


def test_list_activities_filter_by_status(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Status Filter Customer")
    _create_activity(client, auth_headers, customer_id, subject="Open one", status="open")
    _create_activity(
        client, auth_headers, customer_id, subject="Done one", status="completed"
    )

    response = client.get(
        "/api/v1/activities?status=completed",
        headers=auth_headers,
    )
    assert response.status_code == 200
    items = [i for i in response.json()["items"] if i["customer_id"] == customer_id]
    assert len(items) == 1
    assert items[0]["status"] == "completed"


def test_list_activities_filter_by_date_range(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Date Filter Customer")
    _create_activity(
        client,
        auth_headers,
        customer_id,
        subject="In range",
        activity_date="2026-03-15T10:00:00+00:00",
    )
    _create_activity(
        client,
        auth_headers,
        customer_id,
        subject="Out of range",
        activity_date="2025-01-01T10:00:00+00:00",
    )

    response = client.get(
        "/api/v1/activities?dateFrom=2026-03-01&dateTo=2026-03-31",
        headers=auth_headers,
    )
    assert response.status_code == 200
    items = [i for i in response.json()["items"] if i["customer_id"] == customer_id]
    assert len(items) == 1
    assert items[0]["subject"] == "In range"


def test_get_activity_detail_includes_customer_name(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Detail Name Customer")
    created = _create_activity(client, auth_headers, customer_id, subject="Detail subject")
    activity_id = created.json()["id"]

    response = client.get(f"/api/v1/activities/{activity_id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["subject"] == "Detail subject"
    assert body["customer_name"] == "Detail Name Customer"


def test_bulk_delete_activities_hard_deletes(client, auth_headers, db_session):
    from uuid import UUID

    from app.modules.activities.infrastructure.persistence.models import ActivityModel

    customer_id = _create_customer(client, auth_headers, "Bulk Delete Customer")
    a1 = _create_activity(client, auth_headers, customer_id, subject="Bulk 1").json()["id"]
    a2 = _create_activity(client, auth_headers, customer_id, subject="Bulk 2").json()["id"]
    a3 = _create_activity(client, auth_headers, customer_id, subject="Keep").json()["id"]
    missing = str(uuid4())

    response = client.post(
        "/api/v1/activities/bulk-delete",
        json={"activity_ids": [a1, a2, missing]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["deleted_count"] == 2
    assert body["not_found_count"] == 1
    assert set(body["deleted_ids"]) == {a1, a2}
    assert body["not_found_ids"] == [missing]

    assert client.get(f"/api/v1/activities/{a1}", headers=auth_headers).status_code == 404
    assert client.get(f"/api/v1/activities/{a2}", headers=auth_headers).status_code == 404
    assert client.get(f"/api/v1/activities/{a3}", headers=auth_headers).status_code == 200

    db_session.expire_all()
    assert db_session.get(ActivityModel, UUID(a1)) is None
    assert db_session.get(ActivityModel, UUID(a2)) is None
    assert db_session.get(ActivityModel, UUID(a3)) is not None

    org_list = client.get(
        f"/api/v1/activities?customerId={customer_id}",
        headers=auth_headers,
    )
    assert pagination_from(org_list.json())["totalItems"] == 1


def test_hard_delete_nulls_worklist_last_activity_id(client, auth_headers, db_session, organization_id):
    """Inbound FK ON DELETE SET NULL — worklist row must survive activity hard delete."""
    from datetime import UTC, datetime
    from uuid import UUID

    from app.modules.activities.infrastructure.persistence.models import ActivityModel
    from app.modules.todos.infrastructure.persistence.models import (
        TodoModel,
        TodoWorklistStateModel,
    )

    customer_id = _create_customer(client, auth_headers, "Worklist FK Customer")
    activity_id = _create_activity(client, auth_headers, customer_id).json()["id"]

    now = datetime.now(tz=UTC)
    todo_id = uuid4()
    state_id = uuid4()
    db_session.add(
        TodoModel(
            id=todo_id,
            organization_id=organization_id,
            title="Worklist FK Todo",
            status="todo",
            priority="normal",
            category="genel_gorev",
            created_by=organization_id,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        TodoWorklistStateModel(
            id=state_id,
            organization_id=organization_id,
            todo_id=todo_id,
            customer_id=UUID(customer_id),
            participation_id=None,
            primary_status="open",
            last_activity_id=UUID(activity_id),
            last_outcome_id=None,
            follow_up_at=None,
            last_note_summary="note",
            last_activity_at=now,
            last_actor_user_id=None,
            action_required=True,
            data_problem=False,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    delete_response = client.delete(f"/api/v1/activities/{activity_id}", headers=auth_headers)
    assert delete_response.status_code == 204

    db_session.expire_all()
    assert db_session.get(ActivityModel, UUID(activity_id)) is None
    state = db_session.get(TodoWorklistStateModel, state_id)
    assert state is not None
    assert state.last_activity_id is None
    assert state.action_required is True


def test_activities_delete_denied_returns_403(client, auth_headers):
    from app.modules.activities.api.dependencies import (
        get_authorization_adapter as get_activity_authorization_adapter,
    )
    from tests.modules.test_endpoint_permission_enforcement import SelectiveAuthorization

    customer_id = _create_customer(client, auth_headers, "Delete Denied Customer")
    activity_id = _create_activity(client, auth_headers, customer_id).json()["id"]

    client.app.dependency_overrides[get_activity_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.activities.delete"}
    )
    try:
        response = client.delete(f"/api/v1/activities/{activity_id}", headers=auth_headers)
        assert response.status_code == 403
        list_response = client.get(f"/api/v1/activities/{activity_id}", headers=auth_headers)
        assert list_response.status_code == 200
    finally:
        client.app.dependency_overrides.pop(get_activity_authorization_adapter, None)


def test_activities_list_denied_returns_403(client, auth_headers):
    from app.modules.activities.api.dependencies import (
        get_authorization_adapter as get_activity_authorization_adapter,
    )
    from tests.modules.test_endpoint_permission_enforcement import SelectiveAuthorization

    client.app.dependency_overrides[get_activity_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.activities.read"}
    )
    try:
        response = client.get("/api/v1/activities", headers=auth_headers)
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_activity_authorization_adapter, None)

from uuid import UUID

from app.modules.activities.domain.value_objects import ActivityType
from app.modules.activities.infrastructure.persistence.models import ActivityModel
from app.modules.todos.domain.value_objects import TodoCategory


def _create_customer(client, auth_headers, name="Complete Activity Customer"):
    response = client.post(
        "/api/v1/customers",
        json={"display_name": name, "status": "active"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_fair(client, auth_headers, name="Complete Activity Fair"):
    response = client.post(
        "/api/v1/fairs",
        json={"name": name},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_todo(client, auth_headers, **overrides):
    payload = {"title": "Complete me"}
    payload.update(overrides)
    return client.post("/api/v1/todos", json=payload, headers=auth_headers)


def _find_task_completed(client, auth_headers, *, todo_id=None, fair_id=None):
    params = {"activityType": "task_completed"}
    if fair_id is not None:
        params["fairId"] = fair_id
    response = client.get("/api/v1/activities", headers=auth_headers, params=params)
    assert response.status_code == 200
    items = response.json()["items"]
    if todo_id is not None:
        items = [item for item in items if item.get("todo_id") == todo_id]
    return items


def test_complete_todo_with_customer_creates_activity(client, auth_headers):
    customer_id = _create_customer(client, auth_headers)
    todo = _create_todo(client, auth_headers, customer_id=customer_id, title="Customer only")
    assert todo.status_code == 201
    todo_id = todo.json()["id"]

    complete = client.post(f"/api/v1/todos/{todo_id}/complete", headers=auth_headers)
    assert complete.status_code == 200
    assert complete.json()["status"] == "done"

    activities = _find_task_completed(client, auth_headers, todo_id=todo_id)
    assert len(activities) == 1
    activity = activities[0]
    assert activity["type"] == "task_completed"
    assert activity["customer_id"] == customer_id
    assert activity["fair_id"] is None
    assert activity["todo_id"] == todo_id
    assert activity["source"] == "system"
    assert activity["status"] == "completed"
    assert activity["subject"] == "Görev tamamlandı: Customer only"
    assert activity["related_todo_id"] == todo_id


def test_complete_todo_with_fair_creates_activity(client, auth_headers):
    fair_id = _create_fair(client, auth_headers, "Fair only")
    todo = _create_todo(client, auth_headers, source_fair_id=fair_id, title="Fair only todo")
    assert todo.status_code == 201
    todo_id = todo.json()["id"]

    complete = client.post(f"/api/v1/todos/{todo_id}/complete", headers=auth_headers)
    assert complete.status_code == 200

    activities = _find_task_completed(client, auth_headers, todo_id=todo_id)
    assert len(activities) == 1
    activity = activities[0]
    assert activity["customer_id"] is None
    assert activity["fair_id"] == fair_id
    assert activity["todo_id"] == todo_id


def test_complete_todo_with_customer_and_fair(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Both Customer")
    fair_id = _create_fair(client, auth_headers, "Both Fair")
    todo = _create_todo(
        client,
        auth_headers,
        customer_id=customer_id,
        source_fair_id=fair_id,
        title="Both links",
    )
    assert todo.status_code == 201
    todo_id = todo.json()["id"]

    complete = client.post(f"/api/v1/todos/{todo_id}/complete", headers=auth_headers)
    assert complete.status_code == 200

    activities = _find_task_completed(client, auth_headers, todo_id=todo_id)
    assert len(activities) == 1
    activity = activities[0]
    assert activity["customer_id"] == customer_id
    assert activity["fair_id"] == fair_id


def test_complete_todo_with_neither_customer_nor_fair(client, auth_headers):
    todo = _create_todo(client, auth_headers, title="No links")
    assert todo.status_code == 201
    todo_id = todo.json()["id"]

    complete = client.post(f"/api/v1/todos/{todo_id}/complete", headers=auth_headers)
    assert complete.status_code == 200

    activities = _find_task_completed(client, auth_headers, todo_id=todo_id)
    assert len(activities) == 1
    activity = activities[0]
    assert activity["customer_id"] is None
    assert activity["fair_id"] is None
    assert activity["todo_id"] == todo_id
    assert activity["type"] == ActivityType.TASK_COMPLETED


def test_complete_todo_with_note(client, auth_headers):
    todo = _create_todo(client, auth_headers, title="With note")
    todo_id = todo.json()["id"]

    complete = client.post(
        f"/api/v1/todos/{todo_id}/complete",
        headers=auth_headers,
        json={"note": "Tamamlandı notu"},
    )
    assert complete.status_code == 200

    activities = _find_task_completed(client, auth_headers, todo_id=todo_id)
    assert len(activities) == 1
    assert activities[0]["description"] == "Tamamlandı notu"


def test_complete_todo_idempotent_second_call(client, auth_headers):
    todo = _create_todo(client, auth_headers, title="Idempotent")
    todo_id = todo.json()["id"]

    first = client.post(f"/api/v1/todos/{todo_id}/complete", headers=auth_headers)
    assert first.status_code == 200
    second = client.post(f"/api/v1/todos/{todo_id}/complete", headers=auth_headers)
    assert second.status_code == 200
    assert second.json()["status"] == "done"

    activities = _find_task_completed(client, auth_headers, todo_id=todo_id)
    assert len(activities) == 1


def test_delete_todo_keeps_activity_with_null_todo_id(client, auth_headers, db_session):
    todo = _create_todo(client, auth_headers, title="Delete keeps activity")
    todo_id = todo.json()["id"]

    complete = client.post(f"/api/v1/todos/{todo_id}/complete", headers=auth_headers)
    assert complete.status_code == 200

    activities = _find_task_completed(client, auth_headers, todo_id=todo_id)
    assert len(activities) == 1
    activity_id = activities[0]["id"]

    delete = client.delete(f"/api/v1/todos/{todo_id}", headers=auth_headers)
    assert delete.status_code == 204

    get_activity = client.get(f"/api/v1/activities/{activity_id}", headers=auth_headers)
    assert get_activity.status_code == 200
    body = get_activity.json()
    assert body["todo_id"] is None
    assert body["type"] == "task_completed"

    row = (
        db_session.query(ActivityModel)
        .filter(ActivityModel.id == UUID(activity_id))
        .one()
    )
    assert row.todo_id is None


def test_list_activities_fair_id_filter(client, auth_headers):
    fair_a = _create_fair(client, auth_headers, "Filter Fair A")
    fair_b = _create_fair(client, auth_headers, "Filter Fair B")
    todo_a = _create_todo(
        client, auth_headers, source_fair_id=fair_a, title="Todo A"
    ).json()["id"]
    todo_b = _create_todo(
        client, auth_headers, source_fair_id=fair_b, title="Todo B"
    ).json()["id"]

    assert client.post(f"/api/v1/todos/{todo_a}/complete", headers=auth_headers).status_code == 200
    assert client.post(f"/api/v1/todos/{todo_b}/complete", headers=auth_headers).status_code == 200

    response = client.get(
        "/api/v1/activities",
        headers=auth_headers,
        params={"fairId": fair_a, "activityType": "task_completed"},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    assert all(item["fair_id"] == fair_a for item in items)
    assert any(item["todo_id"] == todo_a for item in items)
    assert not any(item["todo_id"] == todo_b for item in items)


def test_create_todo_rejects_system_category(client, auth_headers):
    for category in (
        TodoCategory.TOPLU_MAIL,
        TodoCategory.SMS,
        TodoCategory.WHATSAPP,
        TodoCategory.VERI_TEMIZLEME,
    ):
        response = _create_todo(client, auth_headers, category=category)
        assert response.status_code == 422, category


def test_update_todo_rejects_system_category(client, auth_headers):
    todo = _create_todo(client, auth_headers)
    todo_id = todo.json()["id"]
    response = client.patch(
        f"/api/v1/todos/{todo_id}",
        headers=auth_headers,
        json={"category": TodoCategory.TOPLU_MAIL},
    )
    assert response.status_code == 422


def test_complete_todo_empty_body_ok(client, auth_headers):
    todo = _create_todo(client, auth_headers, title="Empty body")
    todo_id = todo.json()["id"]
    response = client.post(
        f"/api/v1/todos/{todo_id}/complete",
        headers=auth_headers,
        json={},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "done"

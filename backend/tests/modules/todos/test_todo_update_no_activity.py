"""Regression: Todo create/update must never create Activities.

Activity is created only by explicit POST /todos/{id}/complete.
"""

from unittest.mock import patch
from uuid import UUID

import pytest

from app.modules.activities.infrastructure.persistence.models import ActivityModel
from app.modules.todos.infrastructure.persistence.models import TodoModel


def _create_customer(client, auth_headers, name="No Activity Customer"):
    response = client.post(
        "/api/v1/customers",
        json={"display_name": name, "status": "active"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_fair(client, auth_headers, name="No Activity Fair"):
    response = client.post(
        "/api/v1/fairs",
        json={"name": name},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_todo(client, auth_headers, **overrides):
    payload = {"title": "Independent task"}
    payload.update(overrides)
    return client.post("/api/v1/todos", json=payload, headers=auth_headers)


def _activity_count(client, auth_headers, *, todo_id=None):
    response = client.get("/api/v1/activities", headers=auth_headers, params={"page_size": 100})
    assert response.status_code == 200
    items = response.json()["items"]
    if todo_id is not None:
        items = [item for item in items if item.get("todo_id") == todo_id]
    return len(items), items


def _task_completed_count(client, auth_headers, todo_id):
    response = client.get(
        "/api/v1/activities",
        headers=auth_headers,
        params={"activityType": "task_completed", "page_size": 100},
    )
    assert response.status_code == 200
    return [
        item
        for item in response.json()["items"]
        if item.get("todo_id") == todo_id
    ]


def test_create_todo_does_not_create_activity(client, auth_headers):
    before, _ = _activity_count(client, auth_headers)
    todo = _create_todo(client, auth_headers, title="Create no activity")
    assert todo.status_code == 201
    todo_id = todo.json()["id"]
    after, items = _activity_count(client, auth_headers)
    assert after == before
    assert not any(item.get("todo_id") == todo_id for item in items)


def test_update_title_does_not_create_activity(client, auth_headers):
    todo = _create_todo(client, auth_headers, title="Title before")
    todo_id = todo.json()["id"]
    before, _ = _activity_count(client, auth_headers)

    patch = client.patch(
        f"/api/v1/todos/{todo_id}",
        headers=auth_headers,
        json={"title": "Title after"},
    )
    assert patch.status_code == 200
    assert patch.json()["status"] == "todo"

    after, items = _activity_count(client, auth_headers)
    assert after == before
    assert _task_completed_count(client, auth_headers, todo_id) == []


def test_update_customer_id_does_not_create_activity(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Customer add")
    todo = _create_todo(client, auth_headers, title="Add customer")
    todo_id = todo.json()["id"]
    before, _ = _activity_count(client, auth_headers)

    patch = client.patch(
        f"/api/v1/todos/{todo_id}",
        headers=auth_headers,
        json={"customer_id": customer_id},
    )
    assert patch.status_code == 200
    assert patch.json()["customer_id"] == customer_id
    assert patch.json()["status"] == "todo"

    after, _ = _activity_count(client, auth_headers)
    assert after == before
    assert _task_completed_count(client, auth_headers, todo_id) == []


def test_change_customer_id_does_not_create_activity(client, auth_headers):
    customer_a = _create_customer(client, auth_headers, "Customer A")
    customer_b = _create_customer(client, auth_headers, "Customer B")
    todo = _create_todo(client, auth_headers, title="Change customer", customer_id=customer_a)
    todo_id = todo.json()["id"]
    before, _ = _activity_count(client, auth_headers)

    patch = client.patch(
        f"/api/v1/todos/{todo_id}",
        headers=auth_headers,
        json={"customer_id": customer_b},
    )
    assert patch.status_code == 200
    assert patch.json()["customer_id"] == customer_b

    after, _ = _activity_count(client, auth_headers)
    assert after == before
    assert _task_completed_count(client, auth_headers, todo_id) == []


def test_remove_customer_id_does_not_create_activity(client, auth_headers):
    customer_id = _create_customer(client, auth_headers, "Customer remove")
    todo = _create_todo(client, auth_headers, title="Remove customer", customer_id=customer_id)
    todo_id = todo.json()["id"]
    before, _ = _activity_count(client, auth_headers)

    patch = client.patch(
        f"/api/v1/todos/{todo_id}",
        headers=auth_headers,
        json={"customer_id": None},
    )
    assert patch.status_code == 200
    assert patch.json()["customer_id"] is None

    after, _ = _activity_count(client, auth_headers)
    assert after == before
    assert _task_completed_count(client, auth_headers, todo_id) == []


def test_update_fair_id_does_not_create_activity(client, auth_headers):
    fair_id = _create_fair(client, auth_headers, "Fair add")
    todo = _create_todo(client, auth_headers, title="Add fair")
    todo_id = todo.json()["id"]
    before, _ = _activity_count(client, auth_headers)

    patch = client.patch(
        f"/api/v1/todos/{todo_id}",
        headers=auth_headers,
        json={"source_fair_id": fair_id},
    )
    assert patch.status_code == 200
    assert patch.json()["source_fair_id"] == fair_id
    assert patch.json()["status"] == "todo"

    after, _ = _activity_count(client, auth_headers)
    assert after == before
    assert _task_completed_count(client, auth_headers, todo_id) == []


def test_change_and_remove_fair_does_not_create_activity(client, auth_headers):
    fair_a = _create_fair(client, auth_headers, "Fair A")
    fair_b = _create_fair(client, auth_headers, "Fair B")
    todo = _create_todo(client, auth_headers, title="Change fair", source_fair_id=fair_a)
    todo_id = todo.json()["id"]
    before, _ = _activity_count(client, auth_headers)

    change = client.patch(
        f"/api/v1/todos/{todo_id}",
        headers=auth_headers,
        json={"source_fair_id": fair_b},
    )
    assert change.status_code == 200
    assert change.json()["source_fair_id"] == fair_b

    remove = client.patch(
        f"/api/v1/todos/{todo_id}",
        headers=auth_headers,
        json={"source_fair_id": None},
    )
    assert remove.status_code == 200
    assert remove.json()["source_fair_id"] is None

    after, _ = _activity_count(client, auth_headers)
    assert after == before
    assert _task_completed_count(client, auth_headers, todo_id) == []


def test_complete_creates_exactly_one_task_completed_activity(client, auth_headers):
    todo = _create_todo(client, auth_headers, title="Complete once")
    todo_id = todo.json()["id"]
    assert _task_completed_count(client, auth_headers, todo_id) == []

    complete = client.post(
        f"/api/v1/todos/{todo_id}/complete",
        headers=auth_headers,
        json={"note": "Done note"},
    )
    assert complete.status_code == 200
    assert complete.json()["status"] == "done"

    activities = _task_completed_count(client, auth_headers, todo_id)
    assert len(activities) == 1
    assert activities[0]["description"] == "Done note"
    assert activities[0]["type"] == "task_completed"


def test_second_complete_does_not_create_duplicate_activity(client, auth_headers):
    todo = _create_todo(client, auth_headers, title="Idempotent complete")
    todo_id = todo.json()["id"]

    assert client.post(f"/api/v1/todos/{todo_id}/complete", headers=auth_headers).status_code == 200
    assert client.post(f"/api/v1/todos/{todo_id}/complete", headers=auth_headers).status_code == 200

    assert len(_task_completed_count(client, auth_headers, todo_id)) == 1


def test_complete_atomic_rollback_if_activity_creation_fails(client, auth_headers, db_session):
    """If Activity creation fails, Todo must remain open and no Activity row exists."""
    todo = _create_todo(client, auth_headers, title="Atomic rollback")
    todo_id = todo.json()["id"]

    with patch(
        "app.modules.todos.application.complete_todo.Activity.create",
        side_effect=RuntimeError("forced activity failure"),
    ):
        # TestClient(raise_server_exceptions=True) re-raises after the 500 handler.
        with pytest.raises(RuntimeError, match="forced activity failure"):
            client.post(
                f"/api/v1/todos/{todo_id}/complete",
                headers=auth_headers,
                json={"note": "should not commit"},
            )

    db_session.expire_all()
    todo_uuid = UUID(todo_id)
    row = db_session.query(TodoModel).filter(TodoModel.id == todo_uuid).one()
    assert row.status == "todo"
    assert row.completed_at is None

    activity_rows = (
        db_session.query(ActivityModel)
        .filter(ActivityModel.todo_id == todo_uuid)
        .all()
    )
    assert activity_rows == []


def test_complete_atomic_rollback_if_activity_persist_fails(client, auth_headers, db_session):
    """Activity flush failure must not leave Todo marked done."""
    todo = _create_todo(client, auth_headers, title="Atomic persist rollback")
    todo_id = todo.json()["id"]

    with patch(
        "app.modules.activities.infrastructure.repositories.activity_repository."
        "SqlAlchemyActivityRepository.add",
        side_effect=RuntimeError("forced persist failure"),
    ):
        with pytest.raises(RuntimeError, match="forced persist failure"):
            client.post(
                f"/api/v1/todos/{todo_id}/complete",
                headers=auth_headers,
                json={"note": "should not commit"},
            )

    db_session.expire_all()
    todo_uuid = UUID(todo_id)
    row = db_session.query(TodoModel).filter(TodoModel.id == todo_uuid).one()
    assert row.status == "todo"
    assert row.completed_at is None

    activity_rows = (
        db_session.query(ActivityModel)
        .filter(ActivityModel.todo_id == todo_uuid)
        .all()
    )
    assert activity_rows == []

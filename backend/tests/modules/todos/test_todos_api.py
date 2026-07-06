from datetime import UTC, datetime, timedelta
from uuid import uuid4

from tests.conftest_helpers import pagination_from


def _todo_payload(**overrides):
    payload = {"title": "Test todo"}
    payload.update(overrides)
    return payload


def _create_todo(client, auth_headers, **overrides):
    return client.post("/api/v1/todos", json=_todo_payload(**overrides), headers=auth_headers)


def test_create_and_get_todo(client, auth_headers, organization_id, user_id):
    create_response = _create_todo(client, auth_headers, title="Call supplier")
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["title"] == "Call supplier"
    assert body["status"] == "todo"
    assert body["priority"] == "normal"
    assert body["category"] == "genel_gorev"
    assert body["organization_id"] == str(organization_id)
    assert body["created_by"] == str(user_id)

    todo_id = body["id"]
    get_response = client.get(f"/api/v1/todos/{todo_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == todo_id


def test_list_todos(client, auth_headers):
    _create_todo(client, auth_headers, title="First todo")
    _create_todo(client, auth_headers, title="Second todo")

    list_response = client.get("/api/v1/todos", headers=auth_headers)
    assert list_response.status_code == 200
    body = list_response.json()
    assert pagination_from(body)["totalItems"] == 2
    assert len(body["items"]) == 2


def test_update_todo(client, auth_headers, user_id):
    create_response = _create_todo(client, auth_headers)
    todo_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/todos/{todo_id}",
        json={"title": "Updated todo", "status": "in_progress", "category": "arama"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    body = update_response.json()
    assert body["title"] == "Updated todo"
    assert body["status"] == "in_progress"
    assert body["category"] == "arama"
    assert body["updated_by"] == str(user_id)


def test_get_todo_not_found(client, auth_headers):
    response = client.get(f"/api/v1/todos/{uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_org_isolation(client, auth_headers, user_id, other_organization_id):
    create_response = _create_todo(client, auth_headers, title="Org A only")
    todo_id = create_response.json()["id"]

    other_headers = {
        **auth_headers,
        "X-Organization-Id": str(other_organization_id),
    }
    response = client.get(f"/api/v1/todos/{todo_id}", headers=other_headers)
    assert response.status_code == 404


def test_create_todo_invalid_category(client, auth_headers):
    response = _create_todo(client, auth_headers, category="invalid_category")
    assert response.status_code == 422


def test_list_excludes_archived_todos(client, auth_headers, db_session, organization_id):
    active = _create_todo(client, auth_headers, title="Active item")
    assert active.status_code == 201

    now = datetime.now(tz=UTC)
    from app.modules.todos.domain.entities import Todo
    from app.modules.todos.domain.value_objects import TodoStatus
    from app.modules.todos.infrastructure.repositories.todo_repository import SqlAlchemyTodoRepository

    archived = Todo.create(
        organization_id=organization_id,
        title="Archived item",
        created_by=uuid4(),
        status=TodoStatus.ARCHIVED,
        now=now,
    )
    SqlAlchemyTodoRepository(db_session).add(archived)
    db_session.flush()

    list_response = client.get("/api/v1/todos", headers=auth_headers)
    assert list_response.status_code == 200
    body = list_response.json()
    titles = [item["title"] for item in body["items"]]
    assert pagination_from(body)["totalItems"] == 1
    assert titles == ["Active item"]

    get_archived = client.get(f"/api/v1/todos/{archived.id}", headers=auth_headers)
    assert get_archived.status_code == 200


def test_complete_todo(client, auth_headers):
    create_response = _create_todo(
        client,
        auth_headers,
        deadline=(datetime.now(tz=UTC) - timedelta(days=1)).isoformat(),
    )
    todo_id = create_response.json()["id"]

    complete_response = client.post(f"/api/v1/todos/{todo_id}/complete", headers=auth_headers)
    assert complete_response.status_code == 200
    body = complete_response.json()
    assert body["status"] == "done"
    assert body["completed_at"] is not None
    assert body["is_overdue"] is False


def test_archive_todo(client, auth_headers):
    create_response = _create_todo(client, auth_headers, title="To archive")
    todo_id = create_response.json()["id"]

    archive_response = client.post(f"/api/v1/todos/{todo_id}/archive", headers=auth_headers)
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"

    list_response = client.get("/api/v1/todos", headers=auth_headers)
    assert pagination_from(list_response.json())["totalItems"] == 0


def test_delete_todo_returns_204(client, auth_headers):
    create_response = _create_todo(client, auth_headers)
    todo_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/todos/{todo_id}", headers=auth_headers)
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    get_response = client.get(f"/api/v1/todos/{todo_id}", headers=auth_headers)
    assert get_response.status_code == 404


def test_patch_rejects_done_status(client, auth_headers):
    create_response = _create_todo(client, auth_headers)
    todo_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/todos/{todo_id}",
        json={"status": "done"},
        headers=auth_headers,
    )
    assert update_response.status_code == 422


def test_response_includes_is_overdue(client, auth_headers):
    create_response = _create_todo(
        client,
        auth_headers,
        deadline=(datetime.now(tz=UTC) - timedelta(days=1)).isoformat(),
    )
    assert create_response.json()["is_overdue"] is True


def test_list_filter_by_status(client, auth_headers):
    _create_todo(client, auth_headers, title="Todo item")
    _create_todo(client, auth_headers, title="In progress item", status="in_progress")

    list_response = client.get("/api/v1/todos?status=in_progress", headers=auth_headers)
    body = list_response.json()
    assert pagination_from(body)["totalItems"] == 1
    assert body["items"][0]["status"] == "in_progress"

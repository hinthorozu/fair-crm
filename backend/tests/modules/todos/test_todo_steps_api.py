from datetime import UTC, datetime
from uuid import UUID

from app.modules.todos.infrastructure.persistence.models import TodoModel, TodoStepModel


def _create_todo(client, auth_headers, **overrides):
    payload = {"title": "Checklist parent"}
    payload.update(overrides)
    return client.post("/api/v1/todos", json=payload, headers=auth_headers)


def test_replace_list_and_toggle_todo_steps(client, auth_headers, organization_id, db_session):
    create = _create_todo(client, auth_headers, title="Cook meal")
    assert create.status_code == 201
    todo_id = create.json()["id"]

    replace = client.put(
        f"/api/v1/todos/{todo_id}/steps",
        headers=auth_headers,
        json={
            "steps": [
                {"title": "Malzemeleri al"},
                {"title": "Ocağı yak"},
                {"title": "Tavayı ocağa koy"},
            ]
        },
    )
    assert replace.status_code == 200
    steps = replace.json()
    assert [s["title"] for s in steps] == [
        "Malzemeleri al",
        "Ocağı yak",
        "Tavayı ocağa koy",
    ]
    assert [s["sort_order"] for s in steps] == [0, 1, 2]
    assert all(s["is_completed"] is False for s in steps)

    listing = client.get(f"/api/v1/todos/{todo_id}/steps", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 3

    second_id = steps[1]["id"]
    toggle = client.patch(
        f"/api/v1/todos/{todo_id}/steps/{second_id}",
        headers=auth_headers,
        json={"is_completed": True},
    )
    assert toggle.status_code == 200
    assert toggle.json()["is_completed"] is True
    assert toggle.json()["title"] == "Ocağı yak"

    # Replace keeps completion for retained ids; deletes removed; appends new.
    replace2 = client.put(
        f"/api/v1/todos/{todo_id}/steps",
        headers=auth_headers,
        json={
            "steps": [
                {"id": steps[0]["id"], "title": "Malzemeleri al"},
                {"id": second_id, "title": "Ocağı yak"},
                {"title": "Servis et"},
            ]
        },
    )
    assert replace2.status_code == 200
    body = replace2.json()
    assert [s["title"] for s in body] == ["Malzemeleri al", "Ocağı yak", "Servis et"]
    assert body[1]["is_completed"] is True
    assert body[2]["is_completed"] is False

    deleted = client.delete(
        f"/api/v1/todos/{todo_id}/steps/{body[2]['id']}",
        headers=auth_headers,
    )
    assert deleted.status_code == 204
    after = client.get(f"/api/v1/todos/{todo_id}/steps", headers=auth_headers)
    assert len(after.json()) == 2


def test_todo_hard_delete_cascades_steps(client, auth_headers, db_session, organization_id):
    create = _create_todo(client, auth_headers)
    todo_id = create.json()["id"]
    client.put(
        f"/api/v1/todos/{todo_id}/steps",
        headers=auth_headers,
        json={"steps": [{"title": "One"}, {"title": "Two"}]},
    )

    delete = client.delete(f"/api/v1/todos/{todo_id}", headers=auth_headers)
    assert delete.status_code == 204

    from uuid import UUID

    assert db_session.get(TodoModel, UUID(todo_id)) is None
    remaining = (
        db_session.query(TodoStepModel)
        .filter(TodoStepModel.todo_id == UUID(todo_id))
        .count()
    )
    assert remaining == 0


def test_steps_require_parent_todo_in_org(client, auth_headers, other_organization_id):
    create = _create_todo(client, auth_headers)
    todo_id = create.json()["id"]
    other_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    response = client.get(f"/api/v1/todos/{todo_id}/steps", headers=other_headers)
    assert response.status_code == 404


def test_todo_without_steps_lists_empty(client, auth_headers):
    create = _create_todo(client, auth_headers, title="No steps")
    todo_id = create.json()["id"]
    listing = client.get(f"/api/v1/todos/{todo_id}/steps", headers=auth_headers)
    assert listing.status_code == 200
    assert listing.json() == []

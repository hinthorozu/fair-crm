from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.operations.domain.type_registry import default_operation_type_registry
from app.modules.operations.domain.value_objects import OperationType
from app.modules.operations.infrastructure.handlers.manual_task_handler import ManualTaskHandler
from app.modules.operations.infrastructure.handlers.registry import default_handler_registry
from app.modules.operations.infrastructure.persistence.models import OperationModel
from app.modules.todos.infrastructure.persistence.models import TodoModel


@pytest.fixture
def due_at() -> str:
    return datetime(2026, 8, 17, 10, 0, tzinfo=UTC).isoformat()


def test_wizard_metadata_includes_manual_task(client: TestClient, auth_headers: dict):
    response = client.get("/api/v1/operations/wizard-metadata", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    types = {item["type"]: item for item in body["types"]}
    assert OperationType.MANUAL_TASK in types
    manual = types[OperationType.MANUAL_TASK]
    assert manual["handler_registered"] is True
    assert manual["execution_ready"] is True
    assert manual["capabilities"]["requires_worker"] is False
    assert "customer" in manual["supported_sources"]
    assert "fair" in manual["supported_sources"]
    assert "multiple_fairs" not in body["source_kinds"]
    assert "fair" in body["source_kinds"]
    assert "multiple_fairs" not in types["scraper"]["supported_sources"]
    assert "fair" in types["scraper"]["supported_sources"]


def _create_fair(client: TestClient, auth_headers: dict, name: str) -> str:
    response = client.post(
        "/api/v1/fairs",
        headers=auth_headers,
        json={"name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_create_fair_source_with_one_fair(client: TestClient, auth_headers: dict):
    fair_id = _create_fair(client, auth_headers, "Single Fair Source")
    response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "scraper",
            "title": "One fair scraper",
            "source_kind": "fair",
            "source_ids": [fair_id],
            "type_config": {"adapter_key": "tuyap_new"},
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_kind"] == "fair"
    assert body["source_ids"] == [fair_id]
    assert body["source_config"]["source_ids"] == [fair_id]
    assert "fair_id" not in body["source_config"]


def test_create_fair_source_with_multiple_fairs(client: TestClient, auth_headers: dict):
    fair_a = _create_fair(client, auth_headers, "Fair A Source")
    fair_b = _create_fair(client, auth_headers, "Fair B Source")
    response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "bulk_email",
            "title": "Multi fair op",
            "source_kind": "fair",
            "source_ids": [fair_a, fair_b],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_kind"] == "fair"
    assert body["source_ids"] == [fair_a, fair_b]
    assert body["source_config"]["source_ids"] == [fair_a, fair_b]


def test_create_fair_source_rejects_empty_source_ids(client: TestClient, auth_headers: dict):
    response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "scraper",
            "title": "Missing fairs",
            "source_kind": "fair",
            "source_ids": [],
        },
    )
    assert response.status_code == 400
    assert "source_ids" in response.json()["detail"]


def test_create_fair_source_rejects_unknown_fair_id(client: TestClient, auth_headers: dict):
    missing_id = str(uuid4())
    response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "scraper",
            "title": "Unknown fair",
            "source_kind": "fair",
            "source_ids": [missing_id],
        },
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "source_ids" in detail
    assert missing_id in detail


def test_create_rejects_multiple_fairs_source_kind(client: TestClient, auth_headers: dict):
    response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "scraper",
            "title": "Legacy multi",
            "source_kind": "multiple_fairs",
            "source_ids": [str(uuid4())],
        },
    )
    assert response.status_code == 422


def test_type_registry_covers_all_planned_types():
    types = {item.type for item in default_operation_type_registry.list_all()}
    assert types == {
        "scraper",
        "email",
        "bulk_email",
        "enrichment",
        "duplicate_check",
        "data_cleanup",
        "whatsapp",
        "manual_task",
        "reminder",
    }


def test_handler_registry_only_manual_task_ready():
    assert default_handler_registry.list_types() == ["manual_task"]
    handler = default_handler_registry.require("manual_task")
    assert isinstance(handler, ManualTaskHandler)


def test_create_list_detail_manual_task(
    client: TestClient,
    auth_headers: dict,
    organization_id: UUID,
    due_at: str,
):
    create_response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "manual_task",
            "title": "XYZ müşteriyi ara",
            "description": "17.08.2026 tarihinde XYZ müşteriyi ara.",
            "source_kind": "customer",
            "source_config": {},
            "type_config": {
                "title": "XYZ müşteriyi ara",
                "description": "17.08.2026 tarihinde XYZ müşteriyi ara.",
                "customer_id": str(uuid4()),
                "due_at": due_at,
                "priority": "high",
            },
            "priority": "high",
            "start_immediately": False,
        },
    )
    assert create_response.status_code == 201, create_response.text
    created = create_response.json()
    assert created["operation_type"] == "manual_task"
    assert created["status"] == "draft"
    assert created["organization_id"] == str(organization_id)
    assert created["capabilities"]["requires_worker"] is False
    assert created["related_todo_id"] is None

    list_response = client.get("/api/v1/operations", headers=auth_headers)
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["pagination"]["totalItems"] >= 1
    assert any(item["id"] == created["id"] for item in listed["items"])

    detail_response = client.get(f"/api/v1/operations/{created['id']}", headers=auth_headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["operation"]["id"] == created["id"]
    assert detail["runs"] == []


def test_start_manual_task_creates_todo_with_mapping(
    client: TestClient,
    auth_headers: dict,
    db_session: Session,
    organization_id: UUID,
    user_id: UUID,
    due_at: str,
):
    from tests.conftest_customer_helpers import create_test_customer

    customer = create_test_customer(
        db_session,
        organization_id,
        display_name="Manual Task Customer",
    )
    assignee_id = str(uuid4())
    create_response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "manual_task",
            "title": "Ara",
            "source_kind": "customer",
            "type_config": {
                "title": "Ara XYZ",
                "description": "Müşteriyi ara",
                "customer_id": str(customer.id),
                "due_at": due_at,
                "assignee_user_id": assignee_id,
                "priority": "high",
            },
            "priority": "high",
        },
    )
    assert create_response.status_code == 201, create_response.text
    operation_id = create_response.json()["id"]

    start_response = client.post(
        f"/api/v1/operations/{operation_id}/start",
        headers=auth_headers,
    )
    assert start_response.status_code == 200, start_response.text
    started = start_response.json()
    assert started["status"] == "completed"
    assert started["capabilities"]["requires_worker"] is False
    assert started["related_todo_id"] is not None
    assert started["related_resource"] == {
        "type": "todo",
        "id": started["related_todo_id"],
    }
    assert started["latest_run"] is not None
    assert started["latest_run"]["status"] == "completed"
    assert started["latest_run"]["progress"] == 1.0

    todo_id = started["related_todo_id"]
    todo_response = client.get(f"/api/v1/todos/{todo_id}", headers=auth_headers)
    assert todo_response.status_code == 200, todo_response.text
    todo = todo_response.json()
    assert todo["id"] == todo_id
    assert todo["organization_id"] == str(organization_id)
    assert todo["title"] == "Ara XYZ"
    assert todo["description"] == "Müşteriyi ara"
    assert todo["created_by"] == str(user_id)
    assert todo["assignee_user_id"] == assignee_id
    assert todo["customer_id"] == str(customer.id)
    assert todo["priority"] == "high"
    assert todo["status"] == "todo"
    assert todo["deadline"] is not None
    assert todo["deadline"].startswith("2026-08-17")


def test_start_manual_task_without_customer_works(
    client: TestClient,
    auth_headers: dict,
    due_at: str,
):
    create_response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "manual_task",
            "title": "No customer",
            "source_kind": "none",
            "type_config": {
                "title": "Standalone task",
                "due_at": due_at,
                "priority": "normal",
            },
        },
    )
    assert create_response.status_code == 201, create_response.text
    operation_id = create_response.json()["id"]

    start_response = client.post(
        f"/api/v1/operations/{operation_id}/start",
        headers=auth_headers,
    )
    assert start_response.status_code == 200, start_response.text
    todo_id = start_response.json()["related_todo_id"]
    assert todo_id is not None

    todo_response = client.get(f"/api/v1/todos/{todo_id}", headers=auth_headers)
    assert todo_response.status_code == 200
    todo = todo_response.json()
    assert todo["customer_id"] is None
    assert todo["source_fair_id"] is None
    assert todo["title"] == "Standalone task"


def test_start_manual_task_idempotent_no_duplicate_todo(
    client: TestClient,
    auth_headers: dict,
    due_at: str,
):
    create_response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "manual_task",
            "title": "Idempotent",
            "source_kind": "none",
            "type_config": {
                "title": "Idempotent",
                "due_at": due_at,
                "priority": "normal",
            },
        },
    )
    assert create_response.status_code == 201
    operation_id = create_response.json()["id"]

    first = client.post(f"/api/v1/operations/{operation_id}/start", headers=auth_headers)
    assert first.status_code == 200, first.text
    first_body = first.json()
    todo_id = first_body["related_todo_id"]
    assert todo_id is not None

    second = client.post(f"/api/v1/operations/{operation_id}/start", headers=auth_headers)
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["related_todo_id"] == todo_id
    assert second_body["status"] == "completed"

    listed = client.get("/api/v1/todos", headers=auth_headers)
    assert listed.status_code == 200
    matching = [item for item in listed.json()["items"] if item["id"] == todo_id]
    assert len(matching) == 1


def test_cancel_manual_task_preserves_todo(
    client: TestClient,
    auth_headers: dict,
    due_at: str,
):
    create_response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "manual_task",
            "title": "Cancel keep todo",
            "source_kind": "none",
            "type_config": {"title": "Cancel keep todo", "due_at": due_at, "priority": "normal"},
        },
    )
    assert create_response.status_code == 201
    operation_id = create_response.json()["id"]

    started = client.post(f"/api/v1/operations/{operation_id}/start", headers=auth_headers)
    assert started.status_code == 200
    todo_id = started.json()["related_todo_id"]
    assert todo_id is not None

    cancel_response = client.post(
        f"/api/v1/operations/{operation_id}/cancel",
        headers=auth_headers,
    )
    assert cancel_response.status_code == 200, cancel_response.text
    cancelled = cancel_response.json()
    # Completed ops cannot transition to cancelled; Todo history is preserved either way.
    assert cancelled["related_todo_id"] == todo_id

    todo_response = client.get(f"/api/v1/todos/{todo_id}", headers=auth_headers)
    assert todo_response.status_code == 200
    assert todo_response.json()["status"] == "todo"


def test_cancel_draft_manual_task_without_todo(client: TestClient, auth_headers: dict, due_at: str):
    create_response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "manual_task",
            "title": "Draft cancel",
            "source_kind": "none",
            "type_config": {"title": "Draft cancel", "due_at": due_at, "priority": "normal"},
        },
    )
    assert create_response.status_code == 201
    operation_id = create_response.json()["id"]

    cancel_response = client.post(
        f"/api/v1/operations/{operation_id}/cancel",
        headers=auth_headers,
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"
    assert cancel_response.json()["related_todo_id"] is None


def test_retry_manual_task_not_supported(
    client: TestClient,
    auth_headers: dict,
    due_at: str,
):
    create_response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "manual_task",
            "title": "Ara",
            "source_kind": "none",
            "type_config": {"title": "Ara", "priority": "normal"},
            "start_immediately": True,
        },
    )
    assert create_response.status_code == 201, create_response.text
    operation_id = create_response.json()["id"]

    retry_response = client.post(
        f"/api/v1/operations/{operation_id}/retry",
        headers=auth_headers,
    )
    assert retry_response.status_code == 409


def test_create_scraper_without_handler_ok_but_start_conflicts(
    client: TestClient,
    auth_headers: dict,
):
    fair_id = _create_fair(client, auth_headers, "Future scraper fair")
    create_response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "scraper",
            "title": "Future scraper op",
            "source_kind": "fair",
            "source_ids": [fair_id],
            "type_config": {"adapter_key": "tuyap_new"},
        },
    )
    assert create_response.status_code == 201, create_response.text
    operation_id = create_response.json()["id"]
    assert create_response.json()["related_todo_id"] is None

    start_response = client.post(
        f"/api/v1/operations/{operation_id}/start",
        headers=auth_headers,
    )
    assert start_response.status_code == 409


def test_org_isolation(
    client: TestClient,
    auth_headers: dict,
    other_organization_id: UUID,
    user_id: UUID,
    due_at: str,
):
    from app.integrations.kyrox_core.auth import create_test_token

    create_response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "manual_task",
            "title": "Private task",
            "source_kind": "none",
            "type_config": {"title": "Private task", "priority": "normal"},
        },
    )
    assert create_response.status_code == 201
    operation_id = create_response.json()["id"]

    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    detail = client.get(f"/api/v1/operations/{operation_id}", headers=other_headers)
    assert detail.status_code == 404

    listed = client.get("/api/v1/operations", headers=other_headers)
    assert listed.status_code == 200
    assert all(item["id"] != operation_id for item in listed.json()["items"])


def test_manual_task_validation_requires_title(client: TestClient, auth_headers: dict):
    response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "manual_task",
            "title": "fallback",
            "source_kind": "none",
            "type_config": {"priority": "normal"},
        },
    )
    assert response.status_code == 400


def test_repository_persists_operation(
    db_session: Session,
    organization_id: UUID,
    user_id: UUID,
):
    from app.modules.operations.domain.entities import Operation
    from app.modules.operations.infrastructure.repositories.operation_repository import (
        SqlAlchemyOperationRepository,
    )

    repo = SqlAlchemyOperationRepository(db_session)
    now = datetime.now(tz=UTC)
    operation = Operation.create(
        organization_id=organization_id,
        operation_type=OperationType.MANUAL_TASK,
        title="Persist me",
        created_by=user_id,
        now=now,
        type_config={"title": "Persist me"},
    )
    saved = repo.add(operation)
    db_session.flush()

    model = db_session.get(OperationModel, saved.id)
    assert model is not None
    assert model.organization_id == organization_id
    assert model.operation_type == "manual_task"
    assert model.related_todo_id is None


def test_repository_persists_related_todo_id(
    db_session: Session,
    organization_id: UUID,
    user_id: UUID,
):
    from app.modules.operations.domain.entities import Operation
    from app.modules.operations.infrastructure.repositories.operation_repository import (
        SqlAlchemyOperationRepository,
    )
    from app.modules.todos.domain.entities import Todo
    from app.modules.todos.infrastructure.repositories.todo_repository import (
        SqlAlchemyTodoRepository,
    )

    now = datetime.now(tz=UTC)
    todo_repo = SqlAlchemyTodoRepository(db_session)
    todo = Todo.create(
        organization_id=organization_id,
        title="Linked",
        created_by=user_id,
        now=now,
    )
    saved_todo = todo_repo.add(todo)
    db_session.flush()

    op_repo = SqlAlchemyOperationRepository(db_session)
    operation = Operation.create(
        organization_id=organization_id,
        operation_type=OperationType.MANUAL_TASK,
        title="With todo",
        created_by=user_id,
        now=now,
        type_config={"title": "With todo"},
    )
    operation.link_related_todo(saved_todo.id, now=now, updated_by=user_id)
    saved_op = op_repo.add(operation)
    db_session.flush()

    model = db_session.get(OperationModel, saved_op.id)
    assert model is not None
    assert model.related_todo_id == saved_todo.id
    assert db_session.get(TodoModel, saved_todo.id) is not None

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.operations.application.operation_type_seed import (
    CANONICAL_OPERATION_TYPES,
    ensure_default_operation_types,
)
from app.modules.operations.domain.type_registry import default_operation_type_registry
from app.modules.operations.domain.value_objects import OperationType
from app.modules.fairs.api.dependencies import get_fair_scraper_job_runner
from app.modules.operations.infrastructure.handlers.manual_task_handler import ManualTaskHandler
from app.modules.operations.infrastructure.handlers.registry import default_handler_registry
from app.modules.operations.infrastructure.handlers.scraper_handler import ScraperHandler
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
    assert "execution_ready" not in manual
    assert "requires_worker" not in manual["capabilities"]
    assert "execution_ready" not in manual["capabilities"]
    assert "requires_worker" not in body["capabilities_keys"]
    assert "execution_ready" not in body["capabilities_keys"]
    assert "customer" in manual["supported_sources"]
    assert "fair" in manual["supported_sources"]
    assert "multiple_fairs" not in body["source_kinds"]
    assert "fair" in body["source_kinds"]
    assert "multiple_fairs" not in types["scraper"]["supported_sources"]
    assert "fair" in types["scraper"]["supported_sources"]
    scraper = types["scraper"]
    assert scraper["handler_registered"] is True
    assert "execution_ready" not in scraper
    step_ids = [step["id"] for step in scraper["wizard_steps"]]
    assert step_ids == ["fair", "scraper_info", "summary"]
    assert "adapter_key" in scraper["type_config_schema"]["fields"]
    assert "requested_fields" in scraper["type_config_schema"]["fields"]
    assert "source_url" in scraper["type_config_schema"]["fields"]
    assert "scraper_config" in scraper["type_config_schema"]["fields"]


def test_list_operation_types_returns_seeded_catalog(
    client: TestClient,
    auth_headers: dict,
    db_session: Session,
):
    ensure_default_operation_types(db_session)

    response = client.get("/api/v1/operations/types?active_only=true", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    items = body["items"]
    assert len(items) == len(CANONICAL_OPERATION_TYPES)
    by_key = {item["key"]: item for item in items}
    assert by_key["scraper"]["name"] == "Web Scraper"
    assert by_key["scraper"]["is_active"] is True
    assert by_key["scraper"]["sort_order"] == 10
    assert by_key["scraper"]["supports_retry"] is True
    assert "execution_ready" not in by_key["scraper"]
    assert "requires_worker" not in by_key["scraper"]
    assert "execution_ready" not in by_key["email"]
    assert "requires_worker" not in by_key["email"]
    keys_in_order = [item["key"] for item in items]
    assert keys_in_order == [key for key, _name, _sort, _caps in CANONICAL_OPERATION_TYPES]

    ensure_default_operation_types(db_session)
    again = client.get("/api/v1/operations/types?active_only=true", headers=auth_headers)
    assert again.status_code == 200
    assert len(again.json()["items"]) == len(CANONICAL_OPERATION_TYPES)


def test_update_operation_type_capabilities_persists(
    client: TestClient,
    auth_headers: dict,
    db_session: Session,
):
    ensure_default_operation_types(db_session)

    response = client.patch(
        "/api/v1/operations/types/email/capabilities",
        headers=auth_headers,
        json={
            "supports_pause": True,
            "supports_resume": False,
            "supports_retry": True,
            "supports_schedule": True,
            "supports_items": True,
            "is_active": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["key"] == "email"
    assert body["supports_pause"] is True
    assert body["supports_retry"] is True
    assert "execution_ready" not in body
    assert "requires_worker" not in body
    assert body["is_active"] is True

    listed = client.get("/api/v1/operations/types?active_only=true", headers=auth_headers)
    assert listed.status_code == 200
    email = next(item for item in listed.json()["items"] if item["key"] == "email")
    assert email["supports_pause"] is True
    assert "execution_ready" not in email

    scraper = next(item for item in listed.json()["items"] if item["key"] == "scraper")
    assert scraper["supports_pause"] is False
    assert "execution_ready" not in scraper

    wizard = client.get("/api/v1/operations/wizard-metadata", headers=auth_headers)
    assert wizard.status_code == 200
    email_meta = next(item for item in wizard.json()["types"] if item["type"] == "email")
    assert email_meta["capabilities"]["supports_pause"] is True
    assert "execution_ready" not in email_meta
    assert "requires_worker" not in email_meta["capabilities"]


def _create_fair(client: TestClient, auth_headers: dict, name: str, **extra) -> str:
    payload = {"name": name, **extra}
    response = client.post(
        "/api/v1/fairs",
        headers=auth_headers,
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _scraper_type_config(**overrides) -> dict:
    payload = {
        "adapter_key": "tuyap_new",
        "requested_fields": ["customerName", "email", "website"],
        "max_pages": 2,
        "use_http": True,
        "scrape_detail": False,
    }
    payload.update(overrides)
    return payload


def test_create_fair_source_with_one_fair(client: TestClient, auth_headers: dict):
    fair_id = _create_fair(
        client,
        auth_headers,
        "Single Fair Source",
        adapter_key="tuyap_new",
        source_url="https://example.com/list",
        scraper_config={"max_pages": 1},
    )
    response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "scraper",
            "title": "One fair scraper",
            "source_kind": "fair",
            "source_ids": [fair_id],
            "type_config": _scraper_type_config(),
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_kind"] == "fair"
    assert body["source_ids"] == [fair_id]
    assert body["source_config"]["source_ids"] == [fair_id]
    assert "fair_id" not in body["source_config"]
    assert "execution_ready" not in body["capabilities"]
    assert "requires_worker" not in body["capabilities"]
    assert body["capabilities"]["supports_retry"] is True


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
            "type_config": _scraper_type_config(),
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
            "type_config": _scraper_type_config(),
        },
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "source_ids" in detail or "fair" in detail.lower()
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


def test_handler_registry_includes_manual_task_and_scraper():
    assert set(default_handler_registry.list_types()) == {"manual_task", "scraper"}
    assert isinstance(default_handler_registry.require("manual_task"), ManualTaskHandler)
    scraper = default_handler_registry.require("scraper")
    assert isinstance(scraper, ScraperHandler)
    assert scraper.capabilities.supports_retry is True


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
    assert "requires_worker" not in created["capabilities"]
    assert "execution_ready" not in created["capabilities"]
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
    assert "requires_worker" not in started["capabilities"]
    assert "execution_ready" not in started["capabilities"]
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


def test_create_and_start_scraper_links_run_and_schedules_job(
    client: TestClient,
    auth_headers: dict,
):
    scheduled: list = []

    class _FakeJobRunner:
        def run_fair_scraper(self, command) -> None:
            scheduled.append(command)

    client.app.dependency_overrides[get_fair_scraper_job_runner] = lambda: _FakeJobRunner()
    try:
        fair_id = _create_fair(
            client,
            auth_headers,
            "Executable scraper fair",
            adapter_key="tuyap_new",
            source_url="https://example.com/brands",
            scraper_config={"max_pages": 1, "use_http": True},
        )
        create_response = client.post(
            "/api/v1/operations",
            headers=auth_headers,
            json={
                "operation_type": "scraper",
                "title": "Executable scraper op",
                "source_kind": "fair",
                "source_ids": [fair_id],
                "type_config": _scraper_type_config(),
                "start_immediately": True,
            },
        )
        assert create_response.status_code == 201, create_response.text
        body = create_response.json()
        assert body["status"] == "active"
        assert body["latest_run"] is not None
        assert body["latest_run"]["status"] == "running"
        result = (body["latest_run"].get("error_details") or {}).get("result") or {}
        assert result.get("scraper_run_id")
        assert result.get("adapter_key") == "tuyap_new"
        assert result.get("requested_fields") == ["customerName", "email", "website"]
        assert len(scheduled) == 1
        assert str(scheduled[0].fair_id) == fair_id
        assert scheduled[0].requested_fields == ["customerName", "email", "website"]
        assert scheduled[0].option_overrides == {
            "max_pages": 2,
            "use_http": True,
            "scrape_detail": False,
        }

        detail = client.get(f"/api/v1/operations/{body['id']}", headers=auth_headers)
        assert detail.status_code == 200, detail.text
        assert detail.json()["operation"]["latest_run"]["status"] == "running"

        cancel = client.post(f"/api/v1/operations/{body['id']}/cancel", headers=auth_headers)
        assert cancel.status_code == 200, cancel.text
        assert cancel.json()["status"] == "cancelled"
    finally:
        client.app.dependency_overrides.pop(get_fair_scraper_job_runner, None)


def test_create_scraper_rejects_enrichment_adapter(
    client: TestClient,
    auth_headers: dict,
):
    fair_id = _create_fair(
        client,
        auth_headers,
        "Enrichment fair",
        adapter_key="tuyap_new",
        source_url="https://example.com/enrich",
    )
    response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "scraper",
            "title": "Bad enrichment scraper",
            "source_kind": "fair",
            "source_ids": [fair_id],
            "type_config": _scraper_type_config(
                adapter_key="customer_contact_enrichment",
                requested_fields=["email", "phone"],
            ),
        },
    )
    assert response.status_code == 400
    assert "enrichment" in response.json()["detail"].lower()


def test_create_scraper_rejects_invalid_adapter(
    client: TestClient,
    auth_headers: dict,
):
    fair_id = _create_fair(
        client,
        auth_headers,
        "Invalid adapter fair",
        adapter_key="tuyap_new",
        source_url="https://example.com/list",
    )
    response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "scraper",
            "title": "Bad adapter",
            "source_kind": "fair",
            "source_ids": [fair_id],
            "type_config": _scraper_type_config(adapter_key="does_not_exist"),
        },
    )
    assert response.status_code == 400
    assert "adapter" in response.json()["detail"].lower()


def test_create_scraper_allows_adapter_override_different_from_fair(
    client: TestClient,
    auth_headers: dict,
):
    fair_id = _create_fair(
        client,
        auth_headers,
        "Override fair",
        adapter_key="tuyap_old",
        source_url="https://example.com/old",
    )
    response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "scraper",
            "title": "Adapter override",
            "source_kind": "fair",
            "source_ids": [fair_id],
            "type_config": _scraper_type_config(
                adapter_key="tuyap_new",
                source_url="https://example.com/override",
                scraper_config={"max_pages": 1, "use_http": True},
            ),
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["type_config"]["adapter_key"] == "tuyap_new"
    assert body["type_config"]["source_url"] == "https://example.com/override"


def test_create_scraper_rejects_invalid_requested_fields(
    client: TestClient,
    auth_headers: dict,
):
    fair_id = _create_fair(
        client,
        auth_headers,
        "Fields fair",
        adapter_key="tuyap_new",
        source_url="https://example.com/fields",
    )
    response = client.post(
        "/api/v1/operations",
        headers=auth_headers,
        json={
            "operation_type": "scraper",
            "title": "Bad fields",
            "source_kind": "fair",
            "source_ids": [fair_id],
            "type_config": _scraper_type_config(
                requested_fields=["customerName", "notARealField"],
            ),
        },
    )
    assert response.status_code == 400
    assert "requested_fields" in response.json()["detail"]


def test_scraper_operation_successful_scrape_and_handoff(
    client: TestClient,
    auth_headers: dict,
    db_session: Session,
    organization_id: UUID,
    user_id: UUID,
):
    from app.modules.scraper.application.fair_scraper_job_runner import (
        FairScraperJobCommand,
        FairScraperJobRunner,
    )
    from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff

    scheduled: list[FairScraperJobCommand] = []

    class _CaptureRunner:
        def run_fair_scraper(self, command: FairScraperJobCommand) -> None:
            scheduled.append(command)

    client.app.dependency_overrides[get_fair_scraper_job_runner] = lambda: _CaptureRunner()
    try:
        fair_id = _create_fair(
            client,
            auth_headers,
            "Handoff scraper fair",
            adapter_key="tuyap_new",
            source_url="https://handoff.example/list",
            scraper_config={"use_http": True},
        )
        create_response = client.post(
            "/api/v1/operations",
            headers=auth_headers,
            json={
                "operation_type": "scraper",
                "title": "Handoff scraper",
                "source_kind": "fair",
                "source_ids": [fair_id],
                "type_config": _scraper_type_config(max_pages=1),
                "start_immediately": True,
            },
        )
        assert create_response.status_code == 201, create_response.text
        body = create_response.json()
        assert len(scheduled) == 1
        command = scheduled[0]

        def _mock_scrape_executor(**_kwargs) -> ScraperImportHandoff:
            return ScraperImportHandoff(
                canonical_rows=[
                    {
                        "company_name": "Handoff Co",
                        "website": "https://handoff.co",
                        "email": "a@handoff.co",
                        "phone": "",
                    }
                ],
                row_metadata=[{}],
            )

        runner = FairScraperJobRunner(
            session_factory=lambda: db_session,
            scrape_executor=_mock_scrape_executor,
        )
        runner.run_fair_scraper(command)
        db_session.expire_all()

        detail = client.get(f"/api/v1/operations/{body['id']}", headers=auth_headers)
        assert detail.status_code == 200, detail.text
        operation = detail.json()["operation"]
        latest = operation["latest_run"]
        assert latest["status"] == "completed"
        result = (latest.get("error_details") or {}).get("result") or {}
        assert result.get("total_rows") == 1
        assert result.get("import_batch_id")
        assert operation["status"] == "completed"

        batch = client.get(
            f"/api/v1/imports/{result['import_batch_id']}",
            headers=auth_headers,
        )
        assert batch.status_code == 200
        assert batch.json()["source_type"] == "scraper"
    finally:
        client.app.dependency_overrides.pop(get_fair_scraper_job_runner, None)


def test_scraper_operation_failed_scrape_maps_status(
    client: TestClient,
    auth_headers: dict,
    db_session: Session,
):
    from app.modules.scraper.application.fair_scraper_job_runner import (
        FairScraperJobCommand,
        FairScraperJobRunner,
    )

    scheduled: list[FairScraperJobCommand] = []

    class _CaptureRunner:
        def run_fair_scraper(self, command: FairScraperJobCommand) -> None:
            scheduled.append(command)

    client.app.dependency_overrides[get_fair_scraper_job_runner] = lambda: _CaptureRunner()
    try:
        fair_id = _create_fair(
            client,
            auth_headers,
            "Fail scraper fair",
            adapter_key="tuyap_new",
            source_url="https://fail.example/list",
        )
        create_response = client.post(
            "/api/v1/operations",
            headers=auth_headers,
            json={
                "operation_type": "scraper",
                "title": "Failing scraper",
                "source_kind": "fair",
                "source_ids": [fair_id],
                "type_config": _scraper_type_config(),
                "start_immediately": True,
            },
        )
        assert create_response.status_code == 201, create_response.text
        body = create_response.json()
        command = scheduled[0]

        def _boom(**_kwargs):
            raise RuntimeError("scrape exploded")

        runner = FairScraperJobRunner(
            session_factory=lambda: db_session,
            scrape_executor=_boom,
        )
        runner.run_fair_scraper(command)
        db_session.expire_all()

        detail = client.get(f"/api/v1/operations/{body['id']}", headers=auth_headers)
        assert detail.status_code == 200
        latest = detail.json()["operation"]["latest_run"]
        assert latest["status"] == "failed"
        assert "exploded" in (latest.get("error_message") or "")

        # Retry creates a new OperationRun and re-schedules scraper execution.
        scheduled.clear()
        retry = client.post(f"/api/v1/operations/{body['id']}/retry", headers=auth_headers)
        assert retry.status_code == 200, retry.text
        retried = retry.json()
        assert retried["latest_run"] is not None
        assert retried["latest_run"]["id"] != latest["id"]
        assert retried["latest_run"]["status"] in {"queued", "running"}
        assert retried["latest_run"]["attempt"] >= 2
        assert len(scheduled) == 1
    finally:
        client.app.dependency_overrides.pop(get_fair_scraper_job_runner, None)


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

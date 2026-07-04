"""Tests for managed adapter CRUD API."""

from fastapi.testclient import TestClient

from app.modules.scraper.types.scraper_site import ScraperSiteKey


def test_create_adapter(client: TestClient, auth_headers):
    response = client.post(
        "/api/v1/scraper/adapters",
        json={
            "adapter_key": "custom_demo",
            "name": "Custom Demo Adapter",
            "description": "Test adapter",
            "status": "experimental",
            "version": "0.1.0",
            "manifest": {"pagination": {"page_size": 25}},
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["adapter_key"] == "custom_demo"
    assert body["name"] == "Custom Demo Adapter"
    assert body["is_active"] is True
    assert body["manifest"] == {"pagination": {"page_size": 25}}


def test_create_adapter_duplicate_key_returns_409(client: TestClient, auth_headers):
    payload = {
        "adapter_key": "duplicate_key",
        "name": "First Adapter",
        "status": "experimental",
    }
    first = client.post("/api/v1/scraper/adapters", json=payload, headers=auth_headers)
    assert first.status_code == 201

    second = client.post("/api/v1/scraper/adapters", json=payload, headers=auth_headers)
    assert second.status_code == 409


def test_list_adapters_includes_registry_and_custom(client: TestClient, auth_headers):
    client.post(
        "/api/v1/scraper/adapters",
        json={"adapter_key": "custom_list", "name": "Custom List Adapter"},
        headers=auth_headers,
    )

    response = client.get("/api/v1/scraper/adapters", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    keys = {item["adapter_key"] for item in payload["items"]}
    assert ScraperSiteKey.TUYAP_NEW in keys
    assert ScraperSiteKey.TUYAP_OLD in keys
    assert "custom_list" in keys
    assert payload["total"] >= 3


def test_get_adapter_detail(client: TestClient, auth_headers):
    client.post(
        "/api/v1/scraper/adapters",
        json={"adapter_key": "detail_adapter", "name": "Detail Adapter"},
        headers=auth_headers,
    )

    response = client.get("/api/v1/scraper/adapters/detail_adapter", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Detail Adapter"


def test_update_adapter(client: TestClient, auth_headers):
    client.post(
        "/api/v1/scraper/adapters",
        json={"adapter_key": "update_me", "name": "Before Update"},
        headers=auth_headers,
    )

    response = client.patch(
        "/api/v1/scraper/adapters/update_me",
        json={"name": "After Update", "status": "stable"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "After Update"
    assert body["status"] == "stable"


def test_deactivate_and_activate_adapter(client: TestClient, auth_headers):
    client.post(
        "/api/v1/scraper/adapters",
        json={"adapter_key": "toggle_me", "name": "Toggle Adapter"},
        headers=auth_headers,
    )

    deactivate = client.post("/api/v1/scraper/adapters/toggle_me/deactivate", headers=auth_headers)
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False

    activate = client.post("/api/v1/scraper/adapters/toggle_me/activate", headers=auth_headers)
    assert activate.status_code == 200
    assert activate.json()["is_active"] is True


def test_soft_deleted_adapter_hidden_from_list(client: TestClient, auth_headers, db_session, organization_id):
    from datetime import UTC, datetime

    from app.modules.scraper.api.dependencies import get_default_scraper_manager
    from app.modules.scraper.infrastructure.repositories.scraper_adapter_repository import ScraperAdapterRepository
    from app.modules.scraper.services.scraper_adapter_service import create_scraper_adapter_service

    create = client.post(
        "/api/v1/scraper/adapters",
        json={"adapter_key": "deleted_adapter", "name": "Deleted Adapter"},
        headers=auth_headers,
    )
    assert create.status_code == 201

    service = create_scraper_adapter_service(
        ScraperAdapterRepository(db_session),
        get_default_scraper_manager(),
    )
    service.soft_delete_adapter(organization_id, "deleted_adapter")
    db_session.flush()

    response = client.get("/api/v1/scraper/adapters", headers=auth_headers)
    assert response.status_code == 200
    keys = {item["adapter_key"] for item in response.json()["items"]}
    assert "deleted_adapter" not in keys


def test_create_adapter_invalid_key_returns_400(client: TestClient, auth_headers):
    response = client.post(
        "/api/v1/scraper/adapters",
        json={"adapter_key": "Invalid-Key", "name": "Bad Key"},
        headers=auth_headers,
    )
    assert response.status_code == 400

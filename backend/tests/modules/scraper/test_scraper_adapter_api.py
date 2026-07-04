"""Tests for managed adapter CRUD API."""

from fastapi.testclient import TestClient

from app.modules.scraper.domain.adapter_engine import AdapterEngineType
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def test_create_adapter_tuyap_new_name_with_static_engine(client: TestClient, auth_headers):
    """Regression: Turkish name slug must not 500 when engine_key is tuyap_new."""
    response = client.post(
        "/api/v1/scraper/adapters",
        json={
            "name": "Tüyap NEW",
            "engine_key": ScraperSiteKey.TUYAP_NEW,
            "requested_fields": ["customerName", "website", "email"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["adapter_key"] == ScraperSiteKey.TUYAP_NEW
    assert body["engine_key"] == ScraperSiteKey.TUYAP_NEW
    assert body["engine_type"] == AdapterEngineType.STATIC.value
    assert body["name"] == "Tüyap NEW"
    assert body["id"] is not None
    assert body["manifest"]["requested_fields"] == ["customerName", "website", "email"]


def test_create_adapter_with_auto_key_from_name(client: TestClient, auth_headers):
    response = client.post(
        "/api/v1/scraper/adapters",
        json={
            "name": "Tüyap Ambalaj 2026",
            "engine_key": ScraperSiteKey.TUYAP_NEW,
            "requested_fields": ["customerName", "website"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["adapter_key"] == "tuyap_ambalaj_2026"
    assert body["engine_key"] == ScraperSiteKey.TUYAP_NEW
    assert body["engine_type"] == AdapterEngineType.STATIC.value
    assert body["name"] == "Tüyap Ambalaj 2026"
    assert body["id"] is not None


def test_create_dynamic_adapter_without_static_engine(client: TestClient, auth_headers):
    response = client.post(
        "/api/v1/scraper/adapters",
        json={
            "name": "Dynamic Demo Adapter",
            "requested_fields": ["customerName"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["adapter_key"] == "dynamic_demo_adapter"
    assert body["engine_key"] == "dynamic_demo_adapter"
    assert body["engine_type"] == AdapterEngineType.DYNAMIC.value


def test_create_adapter_duplicate_auto_key_gets_suffix(client: TestClient, auth_headers):
    first = client.post(
        "/api/v1/scraper/adapters",
        json={"name": "Demo Adapter", "engine_key": ScraperSiteKey.TUYAP_NEW},
        headers=auth_headers,
    )
    assert first.status_code == 201
    assert first.json()["adapter_key"] == "demo_adapter"

    second = client.post(
        "/api/v1/scraper/adapters",
        json={"name": "Demo Adapter", "engine_key": ScraperSiteKey.TUYAP_OLD},
        headers=auth_headers,
    )
    assert second.status_code == 201
    assert second.json()["adapter_key"] == "demo_adapter_2"


def test_create_adapter_duplicate_key_returns_409(client: TestClient, auth_headers):
    payload = {
        "adapter_key": "duplicate_key",
        "name": "First Adapter",
        "engine_key": ScraperSiteKey.TUYAP_NEW,
    }
    first = client.post("/api/v1/scraper/adapters", json=payload, headers=auth_headers)
    assert first.status_code == 201

    second = client.post("/api/v1/scraper/adapters", json=payload, headers=auth_headers)
    assert second.status_code == 409


def test_list_adapters_includes_registry_and_custom(client: TestClient, auth_headers):
    client.post(
        "/api/v1/scraper/adapters",
        json={"name": "Custom List Adapter", "engine_key": ScraperSiteKey.TUYAP_NEW},
        headers=auth_headers,
    )

    response = client.get("/api/v1/scraper/adapters", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    keys = {item["adapter_key"] for item in payload["items"]}
    assert ScraperSiteKey.TUYAP_NEW in keys
    assert ScraperSiteKey.TUYAP_OLD in keys
    assert "custom_list_adapter" in keys
    assert payload["total"] >= 3


def test_get_adapter_detail(client: TestClient, auth_headers):
    client.post(
        "/api/v1/scraper/adapters",
        json={"name": "Detail Adapter", "engine_key": ScraperSiteKey.TUYAP_NEW},
        headers=auth_headers,
    )

    response = client.get("/api/v1/scraper/adapters/detail_adapter", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Detail Adapter"


def test_update_adapter(client: TestClient, auth_headers):
    client.post(
        "/api/v1/scraper/adapters",
        json={"adapter_key": "update_me", "name": "Before Update", "engine_key": ScraperSiteKey.TUYAP_NEW},
        headers=auth_headers,
    )

    response = client.patch(
        "/api/v1/scraper/adapters/update_me",
        json={"name": "After Update"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "After Update"
    assert "status" not in body


def test_deactivate_and_activate_adapter(client: TestClient, auth_headers):
    client.post(
        "/api/v1/scraper/adapters",
        json={"adapter_key": "toggle_me", "name": "Toggle Adapter", "engine_key": ScraperSiteKey.TUYAP_NEW},
        headers=auth_headers,
    )

    deactivate = client.post("/api/v1/scraper/adapters/toggle_me/deactivate", headers=auth_headers)
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False

    activate = client.post("/api/v1/scraper/adapters/toggle_me/activate", headers=auth_headers)
    assert activate.status_code == 200
    assert activate.json()["is_active"] is True


def test_deleted_adapter_hidden_from_list(client: TestClient, auth_headers):
    create = client.post(
        "/api/v1/scraper/adapters",
        json={"adapter_key": "deleted_adapter", "name": "Deleted Adapter", "engine_key": ScraperSiteKey.TUYAP_NEW},
        headers=auth_headers,
    )
    assert create.status_code == 201

    delete = client.delete("/api/v1/scraper/adapters/deleted_adapter", headers=auth_headers)
    assert delete.status_code == 204

    response = client.get("/api/v1/scraper/adapters", headers=auth_headers)
    assert response.status_code == 200
    keys = {item["adapter_key"] for item in response.json()["items"]}
    assert "deleted_adapter" not in keys


def test_create_adapter_invalid_explicit_key_returns_400(client: TestClient, auth_headers):
    response = client.post(
        "/api/v1/scraper/adapters",
        json={"adapter_key": "Invalid-Key", "name": "Bad Key", "engine_key": ScraperSiteKey.TUYAP_NEW},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_recreate_deleted_custom_adapter_same_key(client: TestClient, auth_headers):
    first = client.post(
        "/api/v1/scraper/adapters",
        json={
            "adapter_key": "reusable_key",
            "name": "Original Name",
            "engine_key": ScraperSiteKey.TUYAP_NEW,
        },
        headers=auth_headers,
    )
    assert first.status_code == 201
    first_id = first.json()["id"]
    assert first_id is not None

    delete = client.delete("/api/v1/scraper/adapters/reusable_key", headers=auth_headers)
    assert delete.status_code == 204

    hidden = client.get("/api/v1/scraper/adapters", headers=auth_headers)
    assert "reusable_key" not in {item["adapter_key"] for item in hidden.json()["items"]}

    recreate = client.post(
        "/api/v1/scraper/adapters",
        json={
            "adapter_key": "reusable_key",
            "name": "Recreated Name",
            "engine_key": ScraperSiteKey.TUYAP_NEW,
        },
        headers=auth_headers,
    )
    assert recreate.status_code == 201
    body = recreate.json()
    assert body["adapter_key"] == "reusable_key"
    assert body["name"] == "Recreated Name"
    assert body["is_active"] is True
    assert body["id"] is not None
    assert body["id"] != first_id


def test_recreate_registry_adapter_same_key(client: TestClient, auth_headers):
    delete = client.delete(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}",
        headers=auth_headers,
    )
    assert delete.status_code == 204

    hidden = client.get("/api/v1/scraper/adapters", headers=auth_headers)
    assert ScraperSiteKey.TUYAP_NEW not in {item["adapter_key"] for item in hidden.json()["items"]}

    recreate = client.post(
        "/api/v1/scraper/adapters",
        json={
            "adapter_key": ScraperSiteKey.TUYAP_NEW,
            "name": "Recreated Tuyap",
            "engine_key": ScraperSiteKey.TUYAP_NEW,
        },
        headers=auth_headers,
    )
    assert recreate.status_code == 201
    body = recreate.json()
    assert body["adapter_key"] == ScraperSiteKey.TUYAP_NEW
    assert body["name"] == "Recreated Tuyap"
    assert body["is_active"] is True

    listing = client.get("/api/v1/scraper/adapters", headers=auth_headers)
    assert ScraperSiteKey.TUYAP_NEW in {item["adapter_key"] for item in listing.json()["items"]}

    detail = client.get(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}",
        headers=auth_headers,
    )
    assert detail.status_code == 200

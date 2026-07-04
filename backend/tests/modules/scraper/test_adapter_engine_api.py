"""Tests for adapter engine catalog and instance/engine separation."""

from fastapi.testclient import TestClient

from app.modules.scraper.domain.adapter_engine import AdapterEngineType
from app.modules.scraper.services.adapter_instance_resolver import resolve_engine_key
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def test_list_adapter_engines_includes_tuyap_new_static(client: TestClient, auth_headers):
    response = client.get("/api/v1/scraper/engines", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    engines = {item["engine_key"]: item for item in payload["items"]}
    assert ScraperSiteKey.TUYAP_NEW in engines
    engine = engines[ScraperSiteKey.TUYAP_NEW]
    assert engine["engine_type"] == AdapterEngineType.STATIC.value
    assert engine["is_runnable"] is True

    features = {item["key"]: item for item in engine["features"]}
    for key in ("instagram", "facebook", "linkedin", "youtube", "notes", "website", "phone"):
        assert features[key]["enabled"] is True


def test_create_multiple_instances_from_same_static_engine(client: TestClient, auth_headers):
    first = client.post(
        "/api/v1/scraper/adapters",
        json={
            "name": "Tüyap Ambalaj 2026",
            "engine_key": ScraperSiteKey.TUYAP_NEW,
        },
        headers=auth_headers,
    )
    assert first.status_code == 201
    first_body = first.json()
    assert first_body["adapter_key"] == "tuyap_ambalaj_2026"
    assert first_body["engine_key"] == ScraperSiteKey.TUYAP_NEW
    assert first_body["engine_type"] == AdapterEngineType.STATIC.value

    second = client.post(
        "/api/v1/scraper/adapters",
        json={
            "name": "Tüyap Mobilya 2026",
            "engine_key": ScraperSiteKey.TUYAP_NEW,
        },
        headers=auth_headers,
    )
    assert second.status_code == 201
    second_body = second.json()
    assert second_body["adapter_key"] == "tuyap_mobilya_2026"
    assert second_body["engine_key"] == ScraperSiteKey.TUYAP_NEW

    listing = client.get("/api/v1/scraper/adapters", headers=auth_headers)
    keys = {item["adapter_key"] for item in listing.json()["items"]}
    assert "tuyap_ambalaj_2026" in keys
    assert "tuyap_mobilya_2026" in keys


def test_builtin_adapter_exposes_engine_fields(client: TestClient, auth_headers):
    response = client.get(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["adapter_key"] == ScraperSiteKey.TUYAP_NEW
    assert body["engine_key"] == ScraperSiteKey.TUYAP_NEW
    assert body["engine_type"] == AdapterEngineType.STATIC.value


def test_resolve_engine_key_for_instance_record(client, auth_headers, db_session, organization_id):
    create = client.post(
        "/api/v1/scraper/adapters",
        json={
            "name": "Foodist Instance",
            "engine_key": ScraperSiteKey.TUYAP_NEW,
        },
        headers=auth_headers,
    )
    assert create.status_code == 201

    resolved = resolve_engine_key(db_session, organization_id, "foodist_instance")
    assert resolved == ScraperSiteKey.TUYAP_NEW


def test_create_instance_rejects_unknown_engine(client: TestClient, auth_headers):
    response = client.post(
        "/api/v1/scraper/adapters",
        json={
            "adapter_key": "bad_instance",
            "engine_key": "unknown_engine",
            "name": "Bad Instance",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404

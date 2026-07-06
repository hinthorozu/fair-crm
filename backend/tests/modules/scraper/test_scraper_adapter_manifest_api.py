"""Tests for adapter manifest merge and update API."""

from fastapi.testclient import TestClient

from app.modules.scraper.types.scraper_site import ScraperSiteKey


def test_update_adapter_manifest_success(client: TestClient, auth_headers):
    response = client.patch(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/manifest",
        json={
            "display_name": "TÜYAP Updated",
            "version": "1.2.3",
            "last_verified": "2026-07-04",
            "supported_sites": ["foodistexpo.com", "example.test"],
            "notes": "Updated manifest notes",
            "output": {"json_handoff": True, "excel": False},
            "browser": {"requires_js": True, "requires_playwright": False},
            "supports": {"list_scraping": True, "email": False},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["adapter_key"] == ScraperSiteKey.TUYAP_NEW
    assert body["display_name"] == "TÜYAP Updated"
    assert "status" not in body
    assert body["version"] == "1.2.3"
    assert body["notes"] == "Updated manifest notes"
    assert body["supported_sites"] == ["foodistexpo.com", "example.test"]
    assert body["output"]["excel"] is False
    assert body["browser"]["requires_playwright"] is False
    assert body["supports"]["email"] is False

    manifest = client.get(
        f"/api/v1/scraper/manifests/{ScraperSiteKey.TUYAP_NEW}",
        headers=auth_headers,
    )
    assert manifest.status_code == 200
    manifest_body = manifest.json()
    assert manifest_body["display_name"] == "TÜYAP Updated"
    assert manifest_body["notes"] == "Updated manifest notes"
    assert "status" not in manifest_body


def test_update_adapter_manifest_clears_notes(client: TestClient, auth_headers):
    adapter = ScraperSiteKey.TUYAP_NEW
    client.patch(
        f"/api/v1/scraper/adapters/{adapter}/manifest",
        json={"notes": "Temporary notes"},
        headers=auth_headers,
    )

    cleared = client.patch(
        f"/api/v1/scraper/adapters/{adapter}/manifest",
        json={"notes": ""},
        headers=auth_headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["notes"] == ""

    manifest = client.get(
        f"/api/v1/scraper/manifests/{adapter}",
        headers=auth_headers,
    )
    assert manifest.status_code == 200
    assert manifest.json()["notes"] == ""


def test_update_adapter_manifest_rejects_adapter_key_change(client: TestClient, auth_headers):
    response = client.patch(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/manifest",
        json={"adapter_key": "other_adapter", "display_name": "Blocked"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_update_adapter_manifest_rejects_status_field(client: TestClient, auth_headers):
    response = client.patch(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/manifest",
        json={"status": "experimental"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_update_adapter_manifest_accepts_supported_sites_string(client: TestClient, auth_headers):
    response = client.patch(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_OLD}/manifest",
        json={"supported_sites": "site-a.test, site-b.test\nsite-c.test"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["supported_sites"] == ["site-a.test", "site-b.test", "site-c.test"]


def test_get_manifest_returns_default_requested_fields(client: TestClient, auth_headers):
    response = client.get(
        f"/api/v1/scraper/manifests/{ScraperSiteKey.TUYAP_NEW}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "status" not in body
    assert body["requested_fields"] == [
        "customerName",
        "phone",
        "email",
        "address",
        "website",
        "hall",
        "stand",
        "instagram",
        "facebook",
        "linkedin",
        "youtube",
        "notes",
    ]


def test_get_manifest_tuyap_old_default_requested_fields_match_tuyap_new(client: TestClient, auth_headers):
    response = client.get(
        f"/api/v1/scraper/manifests/{ScraperSiteKey.TUYAP_OLD}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["requested_fields"] == [
        "customerName",
        "phone",
        "email",
        "address",
        "website",
        "hall",
        "stand",
        "instagram",
        "facebook",
        "linkedin",
        "youtube",
        "notes",
    ]


def test_update_adapter_manifest_persists_requested_fields(client: TestClient, auth_headers):
    adapter = ScraperSiteKey.TUYAP_NEW
    response = client.patch(
        f"/api/v1/scraper/adapters/{adapter}/manifest",
        json={"requested_fields": ["customerName", "website", "instagram"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["requested_fields"] == ["customerName", "website", "instagram"]

    manifest = client.get(
        f"/api/v1/scraper/manifests/{adapter}",
        headers=auth_headers,
    )
    assert manifest.status_code == 200
    assert manifest.json()["requested_fields"] == ["customerName", "website", "instagram"]


def test_update_adapter_manifest_tuyap_old_persists_supported_fields(client: TestClient, auth_headers):
    adapter = ScraperSiteKey.TUYAP_OLD
    response = client.patch(
        f"/api/v1/scraper/adapters/{adapter}/manifest",
        json={"requested_fields": ["customerName", "email", "instagram", "notes"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["requested_fields"] == ["customerName", "email", "instagram", "notes"]

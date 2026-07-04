"""Tests for adapter manifest merge and update API."""

from fastapi.testclient import TestClient

from app.modules.scraper.types.scraper_site import ScraperSiteKey


def test_update_adapter_manifest_success(client: TestClient, auth_headers):
    response = client.patch(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/manifest",
        json={
            "display_name": "TÜYAP Updated",
            "status": "experimental",
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
    assert body["status"] == "experimental"
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
    assert manifest.json()["display_name"] == "TÜYAP Updated"


def test_update_adapter_manifest_rejects_adapter_key_change(client: TestClient, auth_headers):
    response = client.patch(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/manifest",
        json={"adapter_key": "other_adapter", "display_name": "Blocked"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_update_adapter_manifest_rejects_invalid_status(client: TestClient, auth_headers):
    response = client.patch(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/manifest",
        json={"status": "invalid-status"},
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

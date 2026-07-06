"""Tests for scraper manifest API endpoints."""

from fastapi.testclient import TestClient

from app.modules.scraper.types.scraper_site import ScraperSiteKey


def test_list_scraper_manifests_endpoint_returns_adapter_list_format(client: TestClient, auth_headers):
    response = client.get("/api/v1/scraper/manifests", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert len(payload["items"]) == 3

    keys = {item["adapter_key"] for item in payload["items"]}
    assert keys == {
        ScraperSiteKey.TUYAP_OLD,
        ScraperSiteKey.TUYAP_NEW,
        ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
    }

    new_item = next(item for item in payload["items"] if item["adapter_key"] == ScraperSiteKey.TUYAP_NEW)
    assert new_item["display_name"] == "TÜYAP (New)"
    assert "platform" not in new_item
    assert "supported_sites" not in new_item
    assert "supports" not in new_item
    assert "status" not in new_item
    assert new_item["version"] == "1.0.0"
    assert new_item["last_verified"] == "2026-07-04"
    assert "view" in new_item["actions_available"]
    assert "run" in new_item["actions_available"]

    features = {feature["key"]: feature for feature in new_item["features"]}
    assert features["customerName"]["enabled"] is True
    assert features["instagram"]["enabled"] is True
    assert features["facebook"]["enabled"] is True
    assert features["linkedin"]["enabled"] is True
    assert features["website"]["enabled"] is True
    assert features["phone"]["enabled"] is True
    assert features["notes"]["enabled"] is True


def test_get_scraper_manifest_endpoint(client: TestClient, auth_headers):
    response = client.get(f"/api/v1/scraper/manifests/{ScraperSiteKey.TUYAP_NEW}", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["adapter_key"] == ScraperSiteKey.TUYAP_NEW
    assert payload["display_name"] == "TÜYAP (New)"
    assert "status" not in payload
    assert payload["scraper_version"] == "1.0"
    assert payload["target_site_version"] == "unknown"
    assert payload["last_verified"] == "2026-07-04"
    assert payload["supported_sites"] == ["foodistexpo.com", "foodist.tuyap.online"]
    assert payload["supports"]["detail_scraping"] is True
    assert payload["output"]["excel"] is True
    assert payload["browser"]["requires_playwright"] is True


def test_get_scraper_manifest_not_found(client: TestClient, auth_headers):
    response = client.get("/api/v1/scraper/manifests/unknown", headers=auth_headers)

    assert response.status_code == 404

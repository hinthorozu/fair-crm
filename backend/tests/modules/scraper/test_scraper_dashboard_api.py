"""Tests for adapter management dashboard API."""

from fastapi.testclient import TestClient

from app.modules.scraper.types.scraper_site import ScraperSiteKey


def test_scraper_dashboard_summary_counts(client: TestClient, auth_headers):
    response = client.get("/api/v1/scraper/dashboard", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    summary = payload["summary"]

    assert summary["total_adapters"] == 2
    assert "stable_count" not in summary
    assert "experimental_count" not in summary
    assert "deprecated_count" not in summary
    assert summary["last_run_adapter"] is None
    assert summary["failed_scraper_count"] == 0


def test_scraper_dashboard_adapters_match_manifest_list_format(client: TestClient, auth_headers):
    dashboard = client.get("/api/v1/scraper/dashboard", headers=auth_headers).json()
    manifests = client.get("/api/v1/scraper/manifests", headers=auth_headers).json()

    assert dashboard["adapters"] == manifests["items"]
    assert len(dashboard["adapters"]) == 2

    tuyap_new = next(item for item in dashboard["adapters"] if item["adapter_key"] == ScraperSiteKey.TUYAP_NEW)
    tuyap_old = next(item for item in dashboard["adapters"] if item["adapter_key"] == ScraperSiteKey.TUYAP_OLD)

    assert "status" not in tuyap_new
    assert "status" not in tuyap_old
    assert "platform" not in tuyap_new
    assert "supported_sites" not in tuyap_new
    assert tuyap_old["actions_available"] == ["view", "run"]


def test_scraper_dashboard_adapter_list_columns(client: TestClient, auth_headers):
    response = client.get("/api/v1/scraper/dashboard", headers=auth_headers)
    adapter = response.json()["adapters"][0]

    expected_keys = {
        "adapter_key",
        "display_name",
        "version",
        "features",
        "last_verified",
        "actions_available",
    }
    assert expected_keys.issubset(adapter.keys())
    assert "status" not in adapter
    assert "platform" not in adapter
    assert "supported_sites" not in adapter
    assert "supports" not in adapter

    feature_keys = [feature["key"] for feature in adapter["features"]]
    assert feature_keys == [
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
    assert all({"key", "label", "enabled"}.issubset(feature.keys()) for feature in adapter["features"])


def test_adapter_list_features_reflect_manifest_supports(client: TestClient, auth_headers):
    response = client.get("/api/v1/scraper/manifests", headers=auth_headers)
    old_item = next(
        item for item in response.json()["items"] if item["adapter_key"] == ScraperSiteKey.TUYAP_OLD
    )
    features = {feature["key"]: feature["enabled"] for feature in old_item["features"]}

    assert features["customerName"] is True
    assert features["hall"] is True
    assert features["stand"] is True
    assert features["email"] is True
    assert features["instagram"] is False
    assert features["facebook"] is False
    assert features["linkedin"] is False
    assert features["website"] is False
    assert features["phone"] is False
    assert features["notes"] is False

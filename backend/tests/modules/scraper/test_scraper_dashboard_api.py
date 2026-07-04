"""Tests for adapter management dashboard API."""

from fastapi.testclient import TestClient

from app.modules.scraper.types.scraper_site import ScraperSiteKey


def test_scraper_dashboard_summary_counts(client: TestClient):
    response = client.get("/api/v1/scraper/dashboard")

    assert response.status_code == 200
    payload = response.json()
    summary = payload["summary"]

    assert summary["total_adapters"] == 2
    assert summary["stable_count"] == 1
    assert summary["experimental_count"] == 1
    assert summary["deprecated_count"] == 0
    assert summary["last_run_adapter"] is None
    assert summary["failed_scraper_count"] == 0


def test_scraper_dashboard_adapters_match_manifest_list_format(client: TestClient):
    dashboard = client.get("/api/v1/scraper/dashboard").json()
    manifests = client.get("/api/v1/scraper/manifests").json()

    assert dashboard["adapters"] == manifests["items"]
    assert len(dashboard["adapters"]) == 2

    stable = next(item for item in dashboard["adapters"] if item["adapter_key"] == ScraperSiteKey.TUYAP_NEW)
    experimental = next(item for item in dashboard["adapters"] if item["adapter_key"] == ScraperSiteKey.TUYAP_OLD)

    assert stable["status"] == "stable"
    assert experimental["status"] == "experimental"
    assert "platform" not in stable
    assert "supported_sites" not in stable
    assert experimental["actions_available"] == ["view", "run"]


def test_scraper_dashboard_adapter_list_columns(client: TestClient):
    response = client.get("/api/v1/scraper/dashboard")
    adapter = response.json()["adapters"][0]

    expected_keys = {
        "adapter_key",
        "display_name",
        "status",
        "version",
        "features",
        "last_verified",
        "actions_available",
    }
    assert expected_keys.issubset(adapter.keys())
    assert "platform" not in adapter
    assert "supported_sites" not in adapter
    assert "supports" not in adapter

    feature_keys = [feature["key"] for feature in adapter["features"]]
    assert feature_keys == [
        "list_scraping",
        "detail_scraping",
        "pagination",
        "website",
        "email",
        "phone",
    ]
    assert all({"key", "label", "enabled"}.issubset(feature.keys()) for feature in adapter["features"])


def test_adapter_list_features_reflect_manifest_supports(client: TestClient):
    response = client.get("/api/v1/scraper/manifests")
    old_item = next(
        item for item in response.json()["items"] if item["adapter_key"] == ScraperSiteKey.TUYAP_OLD
    )
    features = {feature["key"]: feature["enabled"] for feature in old_item["features"]}

    assert features["list_scraping"] is True
    assert features["detail_scraping"] is False
    assert features["pagination"] is False
    assert features["website"] is False
    assert features["email"] is True
    assert features["phone"] is False

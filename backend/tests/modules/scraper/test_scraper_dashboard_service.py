"""Tests for adapter management dashboard service."""

from app.modules.scraper.core.manifest_registry import get_manifest_registry
from app.modules.scraper.core.scraper_manager import ScraperManager
from app.modules.scraper.core.scraper_registry import get_scraper_adapter_registry
from app.modules.scraper.manifests.tuyap_new_manifest import TUYAP_NEW_MANIFEST
from app.modules.scraper.manifests.tuyap_old_manifest import TUYAP_OLD_MANIFEST
from app.modules.scraper.normalizers.company_normalizer import CompanyNormalizer
from app.modules.scraper.services.scraper_dashboard_service import (
    ScraperDashboardService,
    build_adapter_features,
    build_dashboard_summary,
)


def test_build_dashboard_summary_from_manifests():
    manifests = [TUYAP_OLD_MANIFEST, TUYAP_NEW_MANIFEST]
    summary = build_dashboard_summary(manifests)

    assert summary["total_adapters"] == 2
    assert "stable_count" not in summary
    assert "experimental_count" not in summary
    assert "deprecated_count" not in summary
    assert summary["last_run_adapter"] is None
    assert summary["failed_scraper_count"] == 0


def test_build_dashboard_summary_accepts_run_stats():
    manifests = [TUYAP_NEW_MANIFEST]
    summary = build_dashboard_summary(
        manifests,
        last_run_adapter="tuyap_new",
        failed_scraper_count=2,
    )

    assert summary["last_run_adapter"] == "tuyap_new"
    assert summary["failed_scraper_count"] == 2


def test_build_adapter_features_from_manifest():
    features = build_adapter_features(TUYAP_NEW_MANIFEST)
    by_key = {feature["key"]: feature for feature in features}

    assert by_key["customerName"] == {"key": "customerName", "label": "customerName", "enabled": True}
    assert by_key["phone"]["enabled"] is True
    assert by_key["website"]["enabled"] is True
    assert by_key["instagram"]["enabled"] is True
    assert by_key["hall"]["enabled"] is True
    assert "list_scraping" not in by_key


def test_dashboard_service_uses_manager_manifests():
    manager = ScraperManager(
        registry=get_scraper_adapter_registry(),
        normalizer=CompanyNormalizer(),
        manifest_registry=get_manifest_registry(),
    )
    service = ScraperDashboardService(manager)

    summary = service.build_summary()
    manifests = service.list_manifests()

    assert summary["total_adapters"] == len(manifests)

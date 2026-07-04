"""Tests for scraper adapter manifest registry."""

import pytest

from app.modules.scraper.adapters.tuyap_new_adapter import TuyapNewAdapter
from app.modules.scraper.adapters.tuyap_old_adapter import TuyapOldAdapter
from app.modules.scraper.core.manifest_registry import ManifestRegistry, get_manifest_registry
from app.modules.scraper.core.scraper_manager import ScraperManager
from app.modules.scraper.core.scraper_registry import ScraperAdapterRegistry, get_scraper_adapter_registry
from app.modules.scraper.manifests import register_builtin_manifests
from app.modules.scraper.manifests.scraper_manifest import ScraperStatus
from app.modules.scraper.manifests.tuyap_new_manifest import TUYAP_NEW_MANIFEST
from app.modules.scraper.manifests.tuyap_old_manifest import TUYAP_OLD_MANIFEST
from app.modules.scraper.normalizers.company_normalizer import CompanyNormalizer
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def test_manifest_registers_in_registry():
    registry = ManifestRegistry()
    register_builtin_manifests(registry)

    assert registry.list_adapter_keys() == sorted([ScraperSiteKey.TUYAP_OLD, ScraperSiteKey.TUYAP_NEW])


def test_registry_returns_all_builtin_manifests():
    registry = get_manifest_registry()
    manifests = registry.list_manifests()

    assert len(manifests) == 2
    keys = {manifest.adapter_key for manifest in manifests}
    assert keys == {ScraperSiteKey.TUYAP_OLD, ScraperSiteKey.TUYAP_NEW}


def test_tuyap_new_manifest_matches_adapter():
    adapter = TuyapNewAdapter()
    manifest = TUYAP_NEW_MANIFEST

    assert manifest.adapter_key == adapter.site_key
    assert manifest.display_name == adapter.display_name
    assert manifest.status == ScraperStatus.STABLE
    assert manifest.supports.list_scraping is True
    assert manifest.supports.detail_scraping is True
    assert manifest.supports.pagination is True
    assert manifest.output.json_handoff is True
    assert manifest.output.excel is True
    assert manifest.scraper_version == "1.0"
    assert manifest.target_site_version == "unknown"
    assert manifest.last_verified == "2026-07-04"


def test_tuyap_old_manifest_matches_adapter():
    adapter = TuyapOldAdapter()
    manifest = TUYAP_OLD_MANIFEST

    assert manifest.adapter_key == adapter.site_key
    assert manifest.display_name == adapter.display_name
    assert manifest.status == ScraperStatus.EXPERIMENTAL
    assert manifest.supports.detail_scraping is False


def test_default_adapter_and_manifest_keys_are_aligned():
    adapter_registry = get_scraper_adapter_registry()
    manifest_registry = get_manifest_registry()

    assert adapter_registry.list_site_keys() == manifest_registry.list_adapter_keys()


def test_scraper_manager_reads_manifests():
    manager = ScraperManager(
        registry=get_scraper_adapter_registry(),
        normalizer=CompanyNormalizer(),
        manifest_registry=get_manifest_registry(),
    )

    manifests = manager.list_manifests()
    manifest = manager.get_manifest(ScraperSiteKey.TUYAP_NEW)

    assert len(manifests) == 2
    assert manifest.adapter_key == ScraperSiteKey.TUYAP_NEW
    assert manifest.supported_sites == ("foodistexpo.com", "foodist.tuyap.online")


def test_manifest_registry_unknown_key_raises():
    registry = ManifestRegistry()
    with pytest.raises(KeyError, match="No scraper manifest"):
        registry.get("unknown")

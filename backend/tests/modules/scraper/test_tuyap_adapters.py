"""Tests for TÜYAP scraper adapter prototypes."""

from uuid import uuid4

from app.modules.scraper.adapters.tuyap_new_adapter import TuyapNewAdapter
from app.modules.scraper.adapters.tuyap_old_adapter import TuyapOldAdapter
from app.modules.scraper.core.scraper_manager import ScraperManager
from app.modules.scraper.core.scraper_registry import ScraperAdapterRegistry, get_scraper_adapter_registry
from app.modules.scraper.dto.raw_company_dto import RawCompanyDto
from app.modules.scraper.normalizers.company_normalizer import CompanyNormalizer
from app.modules.scraper.types.scraper_context import ScraperContext
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def test_tuyap_adapters_registered_in_default_registry():
    registry = get_scraper_adapter_registry()
    site_keys = registry.list_site_keys()

    assert ScraperSiteKey.TUYAP_OLD in site_keys
    assert ScraperSiteKey.TUYAP_NEW in site_keys


def test_tuyap_adapters_selectable_independently():
    registry = get_scraper_adapter_registry()

    old_adapter = registry.get(ScraperSiteKey.TUYAP_OLD)
    new_adapter = registry.get(ScraperSiteKey.TUYAP_NEW)

    assert isinstance(old_adapter, TuyapOldAdapter)
    assert isinstance(new_adapter, TuyapNewAdapter)
    assert old_adapter.site_key != new_adapter.site_key
    assert old_adapter.display_name == "TÜYAP (Old)"
    assert new_adapter.display_name == "TÜYAP (New)"


def test_tuyap_old_adapter_returns_raw_company_dtos():
    adapter = TuyapOldAdapter()
    context = ScraperContext(fair_id=uuid4(), list_url="https://tuyap-old.test/exhibitors")

    rows = adapter.scrape(context)

    assert isinstance(rows, list)
    assert len(rows) >= 1
    assert all(isinstance(row, RawCompanyDto) for row in rows)
    assert rows[0].company_name.startswith("TÜYAP Old Placeholder")


def test_tuyap_new_adapter_returns_raw_company_dtos():
    adapter = TuyapNewAdapter()
    context = ScraperContext(fair_id=uuid4(), list_url="https://tuyap-new.test/exhibitors")

    rows = adapter.scrape(context)

    assert isinstance(rows, list)
    assert len(rows) >= 1
    assert all(isinstance(row, RawCompanyDto) for row in rows)
    assert rows[0].company_name.startswith("TÜYAP New Placeholder")


def test_scraper_manager_runs_tuyap_adapters_by_site_key():
    registry = ScraperAdapterRegistry()
    registry.register(TuyapOldAdapter())
    registry.register(TuyapNewAdapter())
    manager = ScraperManager(registry, CompanyNormalizer())
    context = ScraperContext(list_url="https://tuyap.test/list")

    old_result = manager.run(ScraperSiteKey.TUYAP_OLD, context)
    new_result = manager.run(ScraperSiteKey.TUYAP_NEW, context)

    assert old_result.site_key == ScraperSiteKey.TUYAP_OLD
    assert new_result.site_key == ScraperSiteKey.TUYAP_NEW
    assert old_result.raw_count >= 1
    assert new_result.raw_count >= 1
    assert old_result.metadata["adapter"] == "TÜYAP (Old)"
    assert new_result.metadata["adapter"] == "TÜYAP (New)"

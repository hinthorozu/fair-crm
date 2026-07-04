"""Tests for TÜYAP New adapter Foodist list scraping."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.modules.scraper.adapters.tuyap_new_adapter import (
    BRAND_LIST_LINK_SELECTOR,
    PAGINATION_LINK_SELECTOR,
    TuyapNewAdapter,
    TuyapNewScrapeError,
)
from app.modules.scraper.core.browser_service import BrowserService
from app.modules.scraper.dto.raw_company_dto import RawCompanyDto
from app.modules.scraper.types.scraper_context import ScraperContext

FOODIST_EXAMPLE_TEXT = (
    "2A AKÜZÜM OTOMOTİV A.Ş. Türkiye Detaylı İncele Salon: 12 Stant: 1232A"
)
FOODIST_DETAIL_URL = "https://foodist.tuyap.online/brand/2a-akuzum-otomotiv"


def _context(*, url: str | None = "https://foodist.tuyap.online/brands") -> ScraperContext:
    return ScraperContext(fair_id=uuid4(), list_url=url)


def _mock_browser(*, items_exist: bool = True, list_items: list[dict[str, str]] | None = None) -> MagicMock:
    browser = MagicMock(spec=BrowserService)
    browser.is_launched = True
    browser.new_page = AsyncMock()
    browser.goto = AsyncMock()
    browser.exists = AsyncMock(return_value=items_exist)
    browser.attrs = AsyncMock(return_value=[])
    browser.evaluate = AsyncMock(
        return_value=list_items
        or [
            {
                "detail_url": FOODIST_DETAIL_URL,
                "list_text": FOODIST_EXAMPLE_TEXT,
            }
        ]
    )
    return browser


def test_tuyap_new_adapter_fallback_without_browser():
    adapter = TuyapNewAdapter()
    rows = adapter.scrape(_context())

    assert len(rows) == 2
    assert all(row.metadata.get("placeholder") is True for row in rows)


def test_tuyap_new_adapter_fallback_without_url():
    browser = _mock_browser()
    adapter = TuyapNewAdapter(browser=browser)

    rows = adapter.scrape(ScraperContext(fair_id=uuid4(), list_url=None))

    assert len(rows) == 2
    assert all(row.metadata.get("placeholder") is True for row in rows)
    browser.goto.assert_not_called()


def test_tuyap_new_adapter_parses_foodist_list_item():
    browser = _mock_browser()
    adapter = TuyapNewAdapter(browser=browser)

    rows = adapter.scrape(_context())

    browser.exists.assert_awaited_once_with(BRAND_LIST_LINK_SELECTOR)
    browser.evaluate.assert_awaited_once()
    assert len(rows) == 1
    row = rows[0]
    assert row.company_name == "2A AKÜZÜM OTOMOTİV A.Ş."
    assert row.country == "Türkiye"
    assert row.hall == "12"
    assert row.stand == "1232A"
    assert row.metadata.get("placeholder") is False


def test_tuyap_new_adapter_captures_brand_detail_url():
    browser = _mock_browser()
    adapter = TuyapNewAdapter(browser=browser)

    rows = adapter.scrape(_context())

    assert len(rows) == 1
    row = rows[0]
    assert row.source_url == FOODIST_DETAIL_URL
    assert row.metadata["detail_url"] == FOODIST_DETAIL_URL
    assert "/brand/" in row.metadata["detail_url"]


def test_tuyap_new_adapter_returns_raw_company_dtos_when_items_found():
    browser = _mock_browser()
    adapter = TuyapNewAdapter(browser=browser)

    rows = adapter.scrape(_context())

    assert isinstance(rows, list)
    assert len(rows) == 1
    assert all(isinstance(row, RawCompanyDto) for row in rows)


def test_tuyap_new_adapter_fallback_when_no_brand_links_found():
    browser = _mock_browser(items_exist=False)
    adapter = TuyapNewAdapter(browser=browser)

    rows = adapter.scrape(_context())

    browser.exists.assert_awaited_once_with(BRAND_LIST_LINK_SELECTOR)
    browser.evaluate.assert_not_awaited()
    assert len(rows) == 2
    assert all(row.metadata.get("placeholder") is True for row in rows)


def test_tuyap_new_adapter_raises_when_browser_not_launched():
    browser = _mock_browser()
    browser.is_launched = False
    adapter = TuyapNewAdapter(browser=browser)

    with pytest.raises(TuyapNewScrapeError, match="launch"):
        adapter.scrape(_context())

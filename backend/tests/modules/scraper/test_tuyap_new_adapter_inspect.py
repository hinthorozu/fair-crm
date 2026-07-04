"""Tests for TÜYAP New adapter selector inspection."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.modules.scraper.adapters.tuyap_new_adapter import (
    BRAND_LIST_LINK_SELECTOR,
    TuyapNewAdapter,
    TuyapNewScrapeError,
)
from app.modules.scraper.core.browser_service import BrowserService
from app.modules.scraper.types.scraper_context import ScraperContext


def _context(*, url: str | None = "https://foodist.tuyap.online/brands") -> ScraperContext:
    return ScraperContext(fair_id=uuid4(), list_url=url)


def _mock_browser_for_inspection() -> MagicMock:
    counts = {
        BRAND_LIST_LINK_SELECTOR: 3,
        ".pagination a": 5,
    }
    href_samples = {
        BRAND_LIST_LINK_SELECTOR: [
            "https://foodist.tuyap.online/brand/acme",
            "https://foodist.tuyap.online/brand/beta",
        ],
    }
    text_samples = {
        ".pagination a": ["1", "2", "3"],
    }

    async def query_count(selector: str) -> int:
        return counts.get(selector, 0)

    async def texts(selector: str, *, limit: int = 20) -> list[str]:
        return text_samples.get(selector, [])[:limit]

    async def attrs(selector: str, attr: str, *, limit: int = 20) -> list[str]:
        return href_samples.get(selector, [])[:limit]

    browser = MagicMock(spec=BrowserService)
    browser.is_launched = True
    browser.new_page = AsyncMock()
    browser.goto = AsyncMock()
    browser.query_count = AsyncMock(side_effect=query_count)
    browser.texts = AsyncMock(side_effect=texts)
    browser.attrs = AsyncMock(side_effect=attrs)
    return browser


def test_inspect_selectors_requires_url():
    adapter = TuyapNewAdapter(browser=_mock_browser_for_inspection())
    with pytest.raises(TuyapNewScrapeError, match="url"):
        adapter.inspect_selectors(ScraperContext(list_url=None))


def test_inspect_selectors_requires_browser():
    adapter = TuyapNewAdapter()
    with pytest.raises(TuyapNewScrapeError, match="BrowserService"):
        adapter.inspect_selectors(_context())


def test_inspect_selectors_returns_group_results():
    browser = _mock_browser_for_inspection()
    adapter = TuyapNewAdapter(browser=browser)

    report = adapter.inspect_selectors(_context())

    browser.new_page.assert_awaited_once()
    browser.goto.assert_awaited_once_with("https://foodist.tuyap.online/brands")
    assert report["url"] == "https://foodist.tuyap.online/brands"
    assert "brand_list_links" in report["groups"]
    assert report["groups"]["brand_list_links"]["recommended"] == BRAND_LIST_LINK_SELECTOR
    assert report["groups"]["brand_list_links"]["selectors"][BRAND_LIST_LINK_SELECTOR]["count"] == 3


def test_inspect_selectors_reports_active_constants():
    browser = _mock_browser_for_inspection()
    adapter = TuyapNewAdapter(browser=browser)

    report = adapter.inspect_selectors(_context())

    assert report["active_constants"]["BRAND_LIST_LINK_SELECTOR"] == BRAND_LIST_LINK_SELECTOR
    assert "BRAND_LIST_LINK_SELECTOR" in report["recommended_constants"]

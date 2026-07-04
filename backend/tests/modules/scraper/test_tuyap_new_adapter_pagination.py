"""Tests for TÜYAP New adapter Foodist pagination."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.modules.scraper.adapters.tuyap_new_adapter import (
    BRAND_LIST_LINK_SELECTOR,
    PAGINATION_LINK_SELECTOR,
    TuyapNewAdapter,
)
from app.modules.scraper.core.browser_service import BrowserService
from app.modules.scraper.types.scraper_context import ScraperContext

START_URL = "https://foodist.tuyap.online/brands"
PAGE_2_URL = "https://foodist.tuyap.online/brands?page=2"
PAGE_3_URL = "https://foodist.tuyap.online/brands?page=3"

FOODIST_TEXT_A = "Alpha A.Ş. Türkiye Detaylı İncele Salon: 1 Stant: A1"
FOODIST_TEXT_B = "Beta A.Ş. Türkiye Detaylı İncele Salon: 2 Stant: B2"
BRAND_A_URL = "https://foodist.tuyap.online/brand/alpha"
BRAND_B_URL = "https://foodist.tuyap.online/brand/beta"


def _context(*, max_pages: int | None = None) -> ScraperContext:
    options = {}
    if max_pages is not None:
        options["max_pages"] = max_pages
    return ScraperContext(fair_id=uuid4(), list_url=START_URL, options=options)


def _mock_browser_for_pagination(
    *,
    pagination_hrefs: list[str] | None = None,
    page_items: dict[str, list[dict[str, str]]] | None = None,
) -> MagicMock:
    current_url = {"value": START_URL}
    items_by_page = page_items or {
        START_URL: [{"detail_url": BRAND_A_URL, "list_text": FOODIST_TEXT_A}],
        PAGE_2_URL: [
            {"detail_url": BRAND_A_URL, "list_text": FOODIST_TEXT_A},
            {"detail_url": BRAND_B_URL, "list_text": FOODIST_TEXT_B},
        ],
        PAGE_3_URL: [{"detail_url": BRAND_B_URL, "list_text": FOODIST_TEXT_B}],
    }

    async def goto(url: str) -> None:
        current_url["value"] = url

    async def evaluate(_script: str) -> list[dict[str, str]]:
        return items_by_page.get(current_url["value"], [])

    async def attrs(_selector: str, _attr: str, *, limit: int = 20) -> list[str]:
        return pagination_hrefs or [PAGE_2_URL, PAGE_3_URL, PAGE_2_URL, "#top"]

    browser = MagicMock(spec=BrowserService)
    browser.is_launched = True
    browser.new_page = AsyncMock()
    browser.goto = AsyncMock(side_effect=goto)
    browser.exists = AsyncMock(return_value=True)
    browser.attrs = AsyncMock(side_effect=attrs)
    browser.evaluate = AsyncMock(side_effect=evaluate)
    return browser


def test_build_page_urls_dedupes_pagination_links():
    urls = TuyapNewAdapter._build_page_urls(
        START_URL,
        [PAGE_2_URL, PAGE_2_URL, PAGE_3_URL],
        max_pages=None,
    )

    assert urls == [START_URL, PAGE_2_URL, PAGE_3_URL]


def test_build_page_urls_respects_max_pages_limit():
    urls = TuyapNewAdapter._build_page_urls(
        START_URL,
        [PAGE_2_URL, PAGE_3_URL],
        max_pages=2,
    )

    assert urls == [START_URL, PAGE_2_URL]


def test_scrape_visits_all_pages_when_max_pages_not_set():
    browser = _mock_browser_for_pagination()
    adapter = TuyapNewAdapter(browser=browser)

    adapter.scrape(_context())

    goto_urls = [call.args[0] for call in browser.goto.await_args_list]
    assert goto_urls == [START_URL, PAGE_2_URL, PAGE_3_URL]


def test_scrape_avoids_pagination_loops_with_visited_urls():
    browser = _mock_browser_for_pagination(
        pagination_hrefs=[PAGE_2_URL, START_URL, PAGE_3_URL, PAGE_2_URL],
    )
    adapter = TuyapNewAdapter(browser=browser)

    adapter.scrape(_context())

    goto_urls = [call.args[0] for call in browser.goto.await_args_list]
    assert goto_urls == [START_URL, PAGE_2_URL, PAGE_3_URL]
    assert len(goto_urls) == 3


def test_scrape_dedupes_duplicate_detail_urls_across_pages():
    browser = _mock_browser_for_pagination()
    adapter = TuyapNewAdapter(browser=browser)

    rows = adapter.scrape(_context())

    detail_urls = [row.metadata["detail_url"] for row in rows]
    assert detail_urls == [BRAND_A_URL, BRAND_B_URL]
    assert len(rows) == 2


def test_scrape_respects_max_pages_context_option():
    browser = _mock_browser_for_pagination()
    adapter = TuyapNewAdapter(browser=browser)

    rows = adapter.scrape(_context(max_pages=2))

    goto_urls = [call.args[0] for call in browser.goto.await_args_list]
    assert goto_urls == [START_URL, PAGE_2_URL]
    assert browser.exists.await_count == 2
    assert browser.evaluate.await_count == 2
    assert len(rows) == 2
    assert rows[0].metadata["detail_url"] == BRAND_A_URL
    assert rows[1].metadata["detail_url"] == BRAND_B_URL


def test_scrape_uses_unlimited_pages_when_option_missing():
    assert TuyapNewAdapter._resolve_max_pages(ScraperContext(list_url=START_URL)) is None

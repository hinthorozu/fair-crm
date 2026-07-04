"""Tests for TÜYAP New adapter detail page enrichment."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.modules.scraper.adapters.tuyap_new_adapter import (
    BRAND_LIST_LINK_SELECTOR,
    TuyapNewAdapter,
)
from app.modules.scraper.core.browser_service import BrowserService
from app.modules.scraper.types.scraper_context import ScraperContext

START_URL = "https://foodist.tuyap.online/brands"
DETAIL_URL = "https://foodist.tuyap.online/brand/alpha"
LIST_TEXT = "Alpha A.Ş. Türkiye Detaylı İncele Salon: 1 Stant: A1"

DETAIL_HTML = """
<html><body>
  <div class="schedule-detail-info">
    <p>Kategori: Gıda</p>
    <p>Adres: İstanbul</p>
    <p>Telefon: 0212 444 55 66</p>
    <p>E-posta: info@alpha.test</p>
    <p>Açıklama: Demo açıklama.</p>
    <a href="https://www.alpha.test">Site</a>
    <a href="https://www.instagram.com/alpha">Instagram</a>
    <a href="https://www.linkedin.com/company/alpha">LinkedIn</a>
  </div>
</body></html>
"""


def _context(*, scrape_detail: bool | None = None) -> ScraperContext:
    options: dict[str, bool] = {}
    if scrape_detail is not None:
        options["scrape_detail"] = scrape_detail
    return ScraperContext(
        fair_id=uuid4(),
        list_url=START_URL,
        options=options,
    )


def _mock_browser(*, detail_html: str | None = DETAIL_HTML, detail_error: bool = False) -> MagicMock:
    current_url = {"value": START_URL}

    async def goto(url: str) -> None:
        current_url["value"] = url
        if detail_error and "/brand/" in url:
            raise RuntimeError("detail page timeout")

    async def html() -> str:
        return detail_html or ""

    browser = MagicMock(spec=BrowserService)
    browser.is_launched = True
    browser.new_page = AsyncMock()
    browser.goto = AsyncMock(side_effect=goto)
    browser.exists = AsyncMock(return_value=True)
    browser.attrs = AsyncMock(return_value=[])
    browser.evaluate = AsyncMock(
        return_value=[{"detail_url": DETAIL_URL, "list_text": LIST_TEXT}]
    )
    browser.html = AsyncMock(side_effect=html)
    return browser


def test_scrape_detail_false_does_not_fetch_detail_html():
    browser = _mock_browser()
    adapter = TuyapNewAdapter(browser=browser)

    rows = adapter.scrape(_context(scrape_detail=False))

    assert len(rows) == 1
    browser.html.assert_not_awaited()
    goto_urls = [call.args[0] for call in browser.goto.await_args_list]
    assert DETAIL_URL not in goto_urls
    assert rows[0].email is None
    assert rows[0].metadata.get("detail_scraped") is None


def test_scrape_detail_defaults_to_true():
    browser = _mock_browser()
    adapter = TuyapNewAdapter(browser=browser)

    with patch(
        "app.modules.scraper.adapters.tuyap_new_adapter.validate_website_url",
        return_value=True,
    ):
        rows = adapter.scrape(_context())

    assert len(rows) == 1
    assert rows[0].metadata.get("detail_scraped") is True
    browser.html.assert_awaited_once()


def test_scrape_detail_true_merges_detail_fields():
    browser = _mock_browser()
    adapter = TuyapNewAdapter(browser=browser)

    with patch(
        "app.modules.scraper.adapters.tuyap_new_adapter.validate_website_url",
        return_value=True,
    ):
        rows = adapter.scrape(_context())

    assert len(rows) == 1
    row = rows[0]
    browser.html.assert_awaited_once()
    assert row.company_name == "Alpha A.Ş."
    assert row.hall == "1"
    assert row.stand == "A1"
    assert row.email == "info@alpha.test"
    assert row.phone is not None
    assert row.website == "https://www.alpha.test"
    assert row.address == "İstanbul"
    assert row.extra_fields["category"] == "Gıda"
    assert row.extra_fields["description"] == "Demo açıklama."
    assert "alpha.test" in row.extra_fields["websites"]
    assert row.metadata.get("detail_scraped") is True
    assert row.metadata.get("website_valid") is True
    assert row.extra_fields["instagram_url"] == "https://www.instagram.com/alpha"
    assert row.extra_fields["linkedin_url"] == "https://www.linkedin.com/company/alpha"


def test_scrape_detail_error_keeps_list_data():
    browser = _mock_browser(detail_error=True)
    adapter = TuyapNewAdapter(browser=browser)

    rows = adapter.scrape(_context())

    assert len(rows) == 1
    row = rows[0]
    assert row.company_name == "Alpha A.Ş."
    assert row.country == "Türkiye"
    assert row.hall == "1"
    assert row.stand == "A1"
    assert row.source_url == DETAIL_URL
    assert row.email is None
    assert row.metadata.get("detail_scraped") is None

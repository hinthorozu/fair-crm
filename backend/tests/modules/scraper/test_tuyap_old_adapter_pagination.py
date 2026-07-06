"""Tests for TÜYAP Old adapter pagination and max_pages."""

from unittest.mock import patch
from uuid import uuid4

from app.modules.scraper.adapters.tuyap_old_adapter import TuyapOldAdapter
from app.modules.scraper.fetchers.tuyap_old_http_fetcher import discover_pagination_urls, normalize_page_url
from app.modules.scraper.types.scraper_context import ScraperContext

START_URL = "https://istanbulkitapfuari.com/katilimci-listesi"
PAGE2_URL = "https://istanbulkitapfuari.com/katilimci-listesi?page=2"
PAGE3_URL = "https://istanbulkitapfuari.com/katilimci-listesi?page=3"

PAGINATION_HTML = """
<div class="pagination-wrapper">
  <a href="?page=1">1</a>
  <a href="?page=2" class="active">2</a>
  <a href="?page=3">3</a>
</div>
"""

def _list_html(company_name: str, detail_slug: str) -> str:
    return f"""
<div class="filter-list__item">
  <table class="responsive-table filter-table filter-table-half">
    <tbody>
      <tr>
        <td colspan="5" data-title="Firma Adı">
          <div class="table-block-content">{company_name}</div>
        </td>
        <td colspan="4" data-title="İletişim"></td>
        <td colspan="3" data-title="Konum">
          <div class="salon table-block-content"><span>Salon: 1</span></div>
          <div class="stand table-block-content">Stant: 101</div>
        </td>
        <td colspan="3"><a href="katilimci-listesi/{detail_slug}" class="detail-button">DETAYLAR</a></td>
      </tr>
    </tbody>
  </table>
</div>
"""


LIST_HTML = _list_html("TEST FİRMA A", "test-firma-a-1-3293")
LIST_HTML_B = _list_html("TEST FİRMA B", "test-firma-b-2-3293")


def _context(*, max_pages: int | None = None, scrape_detail: bool = False) -> ScraperContext:
    options: dict[str, object] = {"use_http": True, "scrape_detail": scrape_detail}
    if max_pages is not None:
        options["max_pages"] = max_pages
    return ScraperContext(fair_id=uuid4(), list_url=START_URL, options=options)


def test_discover_pagination_urls_normalizes_relative_links():
    urls = discover_pagination_urls(PAGINATION_HTML, base_url=START_URL)
    assert PAGE2_URL in urls
    assert PAGE3_URL in urls


def test_normalize_page_url_ignores_non_pagination_links():
    assert normalize_page_url("#", base_url=START_URL) is None
    assert normalize_page_url("home", base_url=START_URL) is None


@patch("app.modules.scraper.adapters.tuyap_old_adapter.fetch_html")
def test_scrape_respects_max_pages_context_option(mock_fetch_html):
    mock_fetch_html.side_effect = [PAGINATION_HTML + LIST_HTML, LIST_HTML_B]

    adapter = TuyapOldAdapter()
    rows = adapter.scrape(_context(max_pages=2))

    assert mock_fetch_html.call_count == 2
    assert len(rows) == 2
    assert {row.company_name for row in rows} == {"TEST FİRMA A", "TEST FİRMA B"}


@patch("app.modules.scraper.adapters.tuyap_old_adapter.fetch_html")
def test_scrape_dedupes_duplicate_detail_urls_across_pages(mock_fetch_html):
    mock_fetch_html.side_effect = [PAGINATION_HTML + LIST_HTML, LIST_HTML]

    adapter = TuyapOldAdapter()
    rows = adapter.scrape(_context(max_pages=2))

    assert len(rows) == 1


@patch("app.modules.scraper.adapters.tuyap_old_adapter.fetch_html")
def test_scrape_uses_unlimited_pages_when_option_missing(mock_fetch_html):
    mock_fetch_html.return_value = LIST_HTML

    adapter = TuyapOldAdapter()
    rows = adapter.scrape(_context())

    assert mock_fetch_html.call_count == 1
    assert len(rows) == 1

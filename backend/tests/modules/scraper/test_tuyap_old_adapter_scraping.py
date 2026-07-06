"""Tests for TÜYAP Old adapter list scraping."""

from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from app.modules.scraper.adapters.tuyap_old_adapter import TuyapOldAdapter
from app.modules.scraper.dto.raw_company_dto import RawCompanyDto
from app.modules.scraper.types.scraper_context import ScraperContext

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "tuyap_old"
LIST_URL = "https://istanbulkitapfuari.com/katilimci-listesi"


def _context(**options: object) -> ScraperContext:
    return ScraperContext(
        fair_id=uuid4(),
        list_url=LIST_URL,
        options={"use_http": True, "max_pages": 1, **options},
    )


def test_tuyap_old_adapter_returns_empty_without_url():
    adapter = TuyapOldAdapter()
    rows = adapter.scrape(ScraperContext(fair_id=uuid4(), list_url=None, options={"use_http": True}))
    assert rows == []


def test_tuyap_old_adapter_returns_empty_without_browser_or_http():
    adapter = TuyapOldAdapter()
    rows = adapter.scrape(_context(use_http=False))
    assert rows == []


@patch("app.modules.scraper.adapters.tuyap_old_adapter.fetch_html")
def test_tuyap_old_adapter_parses_list_fixture(mock_fetch_html):
    html = (FIXTURES / "list_page.html").read_text(encoding="utf-8")
    mock_fetch_html.return_value = html

    adapter = TuyapOldAdapter()
    rows = adapter.scrape(_context(scrape_detail=False))

    assert len(rows) == 12
    assert all(isinstance(row, RawCompanyDto) for row in rows)
    assert rows[0].company_name == "21. YÜZYIL EĞİTİM VE KÜLTÜR VAKFI"
    assert rows[0].hall == "6"
    assert rows[0].stand == "649"
    assert rows[0].phone == "+904442839"
    assert rows[0].website == "https://yekuv.org/"
    assert rows[0].metadata.get("placeholder") is False
    assert rows[0].source_url is not None


@patch("app.modules.scraper.adapters.tuyap_old_adapter.fetch_html")
def test_tuyap_old_adapter_captures_detail_url(mock_fetch_html):
    html = (FIXTURES / "list_page.html").read_text(encoding="utf-8")
    mock_fetch_html.return_value = html

    adapter = TuyapOldAdapter()
    rows = adapter.scrape(_context(scrape_detail=False))

    assert "21-yuzyil-egitim-ve-kultur-vakfi" in (rows[0].source_url or "")


@patch("app.modules.scraper.adapters.tuyap_old_adapter.fetch_html")
def test_tuyap_old_adapter_maps_product_groups_to_notes(mock_fetch_html):
    html = (FIXTURES / "list_page.html").read_text(encoding="utf-8")
    mock_fetch_html.return_value = html

    adapter = TuyapOldAdapter()
    rows = adapter.scrape(_context(scrape_detail=False))

    with_groups = next(row for row in rows if row.company_name.startswith("AABİR"))
    assert with_groups.notes is not None
    assert "Egitimmateryalleri" in with_groups.notes
    assert with_groups.extra_fields.get("product_groups") is not None

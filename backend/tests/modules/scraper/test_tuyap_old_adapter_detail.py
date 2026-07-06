"""Tests for TÜYAP Old adapter detail scrape behavior."""

from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from app.modules.scraper.adapters.tuyap_old_adapter import TuyapOldAdapter
from app.modules.scraper.types.scraper_context import ScraperContext

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "tuyap_old"
LIST_URL = "https://istanbulkitapfuari.com/katilimci-listesi"


def _context(*, scrape_detail: bool | None = None, requested_fields: list[str] | None = None) -> ScraperContext:
    options: dict[str, object] = {"use_http": True, "max_pages": 1}
    if scrape_detail is not None:
        options["scrape_detail"] = scrape_detail
    if requested_fields is not None:
        options["requested_fields"] = requested_fields
    return ScraperContext(fair_id=uuid4(), list_url=LIST_URL, options=options)


@patch("app.modules.scraper.adapters.tuyap_old_adapter.fetch_html")
def test_requested_fields_list_only_skips_detail_scrape(mock_fetch_html):
    list_html = (FIXTURES / "list_page.html").read_text(encoding="utf-8")
    mock_fetch_html.return_value = list_html

    adapter = TuyapOldAdapter()
    rows = adapter.scrape(
        _context(
            requested_fields=["customerName", "hall", "stand", "phone", "address", "website"],
        )
    )

    assert len(rows) == 12
    assert mock_fetch_html.call_count == 1
    assert all(row.metadata.get("detail_scraped") is not True for row in rows)


@patch("app.modules.scraper.adapters.tuyap_old_adapter.fetch_html")
def test_requested_fields_notes_triggers_detail_scrape(mock_fetch_html):
    list_html = (FIXTURES / "list_page.html").read_text(encoding="utf-8")
    detail_html = (FIXTURES / "detail_page.html").read_text(encoding="utf-8")
    mock_fetch_html.side_effect = [list_html, detail_html] + [detail_html] * 20

    adapter = TuyapOldAdapter()
    rows = adapter.scrape(_context(requested_fields=["customerName", "notes"]))

    assert len(rows) == 12
    assert mock_fetch_html.call_count == 13
    assert rows[0].metadata.get("detail_scraped") is True
    assert rows[0].notes is not None
    assert "YEKÜV" in (rows[0].notes or "")


@patch("app.modules.scraper.adapters.tuyap_old_adapter.fetch_html")
def test_scrape_detail_false_does_not_fetch_detail_html(mock_fetch_html):
    list_html = (FIXTURES / "list_page.html").read_text(encoding="utf-8")
    mock_fetch_html.return_value = list_html

    adapter = TuyapOldAdapter()
    rows = adapter.scrape(_context(scrape_detail=False))

    assert len(rows) == 12
    assert mock_fetch_html.call_count == 1


@patch("app.modules.scraper.adapters.tuyap_old_adapter.fetch_html")
def test_scrape_detail_true_merges_detail_fields(mock_fetch_html):
    list_html = (FIXTURES / "list_page.html").read_text(encoding="utf-8")
    detail_html = (FIXTURES / "detail_page.html").read_text(encoding="utf-8")
    mock_fetch_html.side_effect = [list_html, detail_html] + [detail_html] * 20

    adapter = TuyapOldAdapter()
    rows = adapter.scrape(_context(scrape_detail=True))

    assert rows[0].metadata.get("detail_scraped") is True
    assert "YEKÜV" in (rows[0].notes or "")


@patch("app.modules.scraper.adapters.tuyap_old_adapter.fetch_html")
def test_scrape_detail_error_keeps_list_data(mock_fetch_html):
    list_html = (FIXTURES / "list_page.html").read_text(encoding="utf-8")

    def _fetch(url: str) -> str:
        if url.rstrip("/").endswith("katilimci-listesi") or "katilimci-listesi?page=" in url:
            return list_html
        raise RuntimeError("detail unavailable")

    mock_fetch_html.side_effect = _fetch

    adapter = TuyapOldAdapter()
    rows = adapter.scrape(_context(scrape_detail=True))

    assert rows[0].company_name == "21. YÜZYIL EĞİTİM VE KÜLTÜR VAKFI"
    assert rows[0].hall == "6"
    assert rows[0].metadata.get("detail_scraped") is not True


@patch("app.modules.scraper.adapters.tuyap_old_adapter.fetch_html")
def test_requested_fields_instagram_triggers_detail_and_merges_social(mock_fetch_html):
    list_html = (FIXTURES / "list_page.html").read_text(encoding="utf-8")
    detail_html = (FIXTURES / "detail_page.html").read_text(encoding="utf-8")
    mock_fetch_html.side_effect = [list_html, detail_html] + [detail_html] * 20

    adapter = TuyapOldAdapter()
    rows = adapter.scrape(_context(requested_fields=["customerName", "instagram"]))

    assert rows[0].metadata.get("detail_scraped") is True
    assert rows[0].extra_fields.get("instagram_url") == "https://www.instagram.com/yekuv_1992/"


@patch("app.modules.scraper.adapters.tuyap_old_adapter.fetch_html")
def test_requested_fields_email_triggers_detail_without_error_when_missing(mock_fetch_html):
    list_html = (FIXTURES / "list_page.html").read_text(encoding="utf-8")
    detail_html = (FIXTURES / "detail_page.html").read_text(encoding="utf-8")
    mock_fetch_html.side_effect = [list_html, detail_html] + [detail_html] * 20

    adapter = TuyapOldAdapter()
    rows = adapter.scrape(_context(requested_fields=["customerName", "email"]))

    assert rows[0].metadata.get("detail_scraped") is True
    assert rows[0].email is None

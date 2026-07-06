"""Tests for tuyap_old detail HTML parser."""

from pathlib import Path

from app.modules.scraper.parsers.tuyap_old_detail_parser import parse_tuyap_old_detail_html

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "tuyap_old"


def test_parse_detail_fixture_extracts_about_text():
    html = (FIXTURES / "detail_page.html").read_text(encoding="utf-8")
    detail = parse_tuyap_old_detail_html(html)

    assert detail.about is not None
    assert "YEKÜV" in detail.about
    assert "1992" in detail.about


def test_parse_detail_fixture_extracts_social_links():
    html = (FIXTURES / "detail_page.html").read_text(encoding="utf-8")
    detail = parse_tuyap_old_detail_html(html)

    assert detail.instagram_url == "https://www.instagram.com/yekuv_1992/"
    assert detail.facebook_url == "https://www.facebook.com/yekuvvakfi"
    assert "linkedin.com" in (detail.linkedin_url or "")
    assert detail.youtube_url is None
    assert detail.email is None

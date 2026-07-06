"""Tests for tuyap_old list HTML parser."""

from pathlib import Path

from app.modules.scraper.parsers.tuyap_old_list_parser import parse_tuyap_old_list_html

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "tuyap_old"
BASE_URL = "https://istanbulkitapfuari.com/katilimci-listesi"


def test_parse_list_fixture_extracts_exhibitors():
    html = (FIXTURES / "list_page.html").read_text(encoding="utf-8")
    items = parse_tuyap_old_list_html(html, base_url=BASE_URL)

    assert len(items) == 12
    first = items[0]
    assert first.company_name == "21. YÜZYIL EĞİTİM VE KÜLTÜR VAKFI"
    assert first.address is not None
    assert "İSTANBUL" in first.address
    assert first.phone == "+904442839"
    assert first.website == "https://yekuv.org/"
    assert first.hall == "6"
    assert first.stand == "649"
    assert first.detail_url is not None
    assert "21-yuzyil-egitim-ve-kultur-vakfi" in first.detail_url


def test_parse_list_fixture_extracts_product_groups():
    html = (FIXTURES / "list_page.html").read_text(encoding="utf-8")
    items = parse_tuyap_old_list_html(html, base_url=BASE_URL)

    with_groups = next(item for item in items if item.company_name.startswith("AABİR"))
    assert "Egitimmateryalleri" in with_groups.product_groups
    assert "Kultur yayinlari" in with_groups.product_groups


def test_parse_list_fixture_skips_empty_product_group_message():
    html = (FIXTURES / "list_page.html").read_text(encoding="utf-8")
    items = parse_tuyap_old_list_html(html, base_url=BASE_URL)

    first = items[0]
    assert first.product_groups == ()

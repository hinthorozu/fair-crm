"""Tests for Foodist brand list HTML extraction."""

from pathlib import Path

from app.modules.scraper.fetchers.foodist_http_fetcher import extract_list_items
from app.modules.scraper.parsers.foodist_list_extract import (
    extract_company_name_from_brand_link_html,
    extract_list_text_from_brand_link_html,
)
from app.modules.scraper.parsers.foodist_list_parser import parse_foodist_list_text

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "foodist_brand_link_snippets.html"

ABEY_INNER_HTML = """
<div class="brand-container">
    <div class="brand-logo">
        <div class="brand-logo-placeholder">AB</div>
    </div>
    <div class="brand-info">
        <h2 class="brand-name">ABEY GIDA TURİZM VE DIŞ TİC. A.Ş.</h2>
        <p class="brand-country">Türkiye</p>
        <button class="border-0 bg-white brand-detail-btn">Detaylı İncele</button>
    </div>
    <div class="brand-location-info">
        <div class="location-item"><span>Salon: 11</span></div>
        <div class="location-item"><span>Stant: 1103B</span></div>
    </div>
    <div class="fair-logo-container"></div>
</div>
"""

AKANLAR_INNER_HTML = """
<div class="brand-container">
    <div class="brand-logo">
        <div class="brand-logo-placeholder">AK</div>
    </div>
    <div class="brand-info">
        <h2 class="brand-name">AKANLAR ÇİKOLATA İÇECEK GIDA SAN. VE NAK. TİC. LTD. ŞTİ.</h2>
        <p class="brand-country">Türkiye</p>
        <button class="border-0 bg-white brand-detail-btn">Detaylı İncele</button>
    </div>
    <div class="brand-location-info">
        <div class="location-item"><span>Salon: 2</span></div>
        <div class="location-item"><span>Stant: 253B</span></div>
    </div>
    <div class="fair-logo-container"></div>
</div>
"""

TWO_A_INNER_HTML = """
<div class="brand-container">
    <div class="brand-logo">
        <div class="brand-logo-placeholder">2A</div>
    </div>
    <div class="brand-info">
        <h2 class="brand-name">2A AKÜZÜM OTOMOTİV A.Ş.</h2>
        <p class="brand-country">Türkiye</p>
        <button class="border-0 bg-white brand-detail-btn">Detaylı İncele</button>
    </div>
    <div class="brand-location-info">
        <div class="location-item"><span>Salon: 12</span></div>
        <div class="location-item"><span>Stant: 1232A</span></div>
    </div>
    <div class="fair-logo-container"></div>
</div>
"""


def test_extract_list_text_ignores_logo_placeholder():
    text = extract_list_text_from_brand_link_html(ABEY_INNER_HTML)

    assert text.startswith("ABEY GIDA TURİZM")
    assert not text.startswith("AB ABEY")
    assert "Salon: 11" in text
    assert "Stant: 1103B" in text


def test_extract_company_name_reads_brand_name_heading():
    assert extract_company_name_from_brand_link_html(AKANLAR_INNER_HTML) == (
        "AKANLAR ÇİKOLATA İÇECEK GIDA SAN. VE NAK. TİC. LTD. ŞTİ."
    )


def test_extract_list_text_end_to_end_parse_akanlar():
    text = extract_list_text_from_brand_link_html(AKANLAR_INNER_HTML)
    parsed = parse_foodist_list_text(text)

    assert parsed is not None
    assert parsed.company_name == "AKANLAR ÇİKOLATA İÇECEK GIDA SAN. VE NAK. TİC. LTD. ŞTİ."
    assert parsed.hall == "2"
    assert parsed.stand == "253B"


def test_extract_list_text_preserves_real_two_a_company_name():
    text = extract_list_text_from_brand_link_html(TWO_A_INNER_HTML)
    parsed = parse_foodist_list_text(text)

    assert parsed is not None
    assert parsed.company_name == "2A AKÜZÜM OTOMOTİV A.Ş."


def test_extract_list_items_from_saved_page_fixture():
    html = FIXTURES.read_text(encoding="utf-8")
    items = extract_list_items(html, base_url="https://www.foodistexpo.com/katilimci-listesi")
    assert len(items) == 1

    parsed = parse_foodist_list_text(items[0]["list_text"])
    assert parsed is not None
    assert parsed.company_name == "ABEY GIDA TURİZM VE DIŞ TİC. A.Ş."
    assert not parsed.company_name.startswith("AB ABEY")

"""Tests for Foodist Expo list text parser."""

from app.modules.scraper.parsers.foodist_list_parser import parse_foodist_list_text

FOODIST_EXAMPLE_TEXT = (
    "2A AKÜZÜM OTOMOTİV A.Ş. Türkiye Detaylı İncele Salon: 12 Stant: 1232A"
)
FOODIST_DETAIL_URL = "https://foodist.tuyap.online/brand/2a-akuzum-otomotiv"


def test_foodist_parser_extracts_company_country_hall_stand():
    parsed = parse_foodist_list_text(FOODIST_EXAMPLE_TEXT, detail_url=FOODIST_DETAIL_URL)

    assert parsed is not None
    assert parsed.company_name == "2A AKÜZÜM OTOMOTİV A.Ş."
    assert parsed.country == "Türkiye"
    assert parsed.hall == "12"
    assert parsed.stand == "1232A"
    assert parsed.detail_url == FOODIST_DETAIL_URL


def test_foodist_parser_extracts_foreign_country():
    text = "ACME GmbH Almanya Detaylı İncele Salon: 7 Stant: B11"
    parsed = parse_foodist_list_text(text)

    assert parsed is not None
    assert parsed.company_name == "ACME GmbH"
    assert parsed.country == "Almanya"
    assert parsed.hall == "7"
    assert parsed.stand == "B11"


def test_foodist_parser_extracts_brands_when_present():
    text = "Demo A.Ş. Markalar: Alpha, Beta Türkiye Detaylı İncele Salon: 1 Stant: A1"
    parsed = parse_foodist_list_text(text)

    assert parsed is not None
    assert parsed.company_name == "Demo A.Ş."
    assert parsed.brands == "Alpha, Beta"
    assert parsed.country == "Türkiye"


def test_foodist_parser_normalizes_unicode_country_variants():
    text = "2A 2A AKÜZÜM OTOMOTİV A.Ş. Türkı̇ye Detaylı İncele Salon: 12 Stant: 1232A"
    parsed = parse_foodist_list_text(text)

    assert parsed is not None
    assert parsed.company_name == "2A AKÜZÜM OTOMOTİV A.Ş."
    assert parsed.country == "Türkiye"
    assert parsed.hall == "12"
    assert parsed.stand == "1232A"


def test_foodist_parser_normalizes_china_unicode_variant():
    text = "INNER MONGOLIA SHILONG CO.,LTD Çı̇n Markalar SHILONG Detaylı İncele Salon: 10 Stant: 1011-7"
    parsed = parse_foodist_list_text(text)

    assert parsed is not None
    assert parsed.country == "Çin"
    assert "Çı" not in (parsed.company_name or "")

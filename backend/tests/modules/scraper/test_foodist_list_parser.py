"""Tests for Foodist Expo list text parser."""

import pytest

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


def test_foodist_parser_strips_logo_placeholder_prefix_from_legacy_flat_text():
    text = (
        "AK AKANLAR ÇİKOLATA İÇECEK GIDA SAN. VE NAK. TİC. LTD. ŞTİ. "
        "Türkiye Detaylı İncele Salon: 2 Stant: 253B"
    )
    parsed = parse_foodist_list_text(text)

    assert parsed is not None
    assert parsed.company_name == "AKANLAR ÇİKOLATA İÇECEK GIDA SAN. VE NAK. TİC. LTD. ŞTİ."


def test_foodist_parser_strips_other_two_letter_logo_prefixes():
    text = "AB ABEY GIDA TURİZM VE DIŞ TİC. A.Ş. Türkiye Detaylı İncele Salon: 11 Stant: 1103B"
    parsed = parse_foodist_list_text(text)

    assert parsed is not None
    assert parsed.company_name == "ABEY GIDA TURİZM VE DIŞ TİC. A.Ş."


def test_foodist_parser_does_not_strip_unrelated_ak_prefix():
    text = "AK STEEL SANAYİ A.Ş. Türkiye Detaylı İncele Salon: 1 Stant: 101"
    parsed = parse_foodist_list_text(text)

    assert parsed is not None
    assert parsed.company_name == "AK STEEL SANAYİ A.Ş."


@pytest.mark.parametrize(
    ("raw_prefix_text", "expected_company_name"),
    [
        (
            "AD ADALILAR KURUYEMİŞ ANONİM ŞİRKETİ Türkiye Detaylı İncele Salon: 3 Stant: 317",
            "ADALILAR KURUYEMİŞ ANONİM ŞİRKETİ",
        ),
        (
            "AG AGRO SEEDS GIDA SAN.VE TİC.LTD.ŞTİ. Türkiye Detaylı İncele Salon: 3 Stant: 318C",
            "AGRO SEEDS GIDA SAN.VE TİC.LTD.ŞTİ.",
        ),
        (
            "AK AKANLAR ÇİKOLATA İÇECEK GIDA SAN. VE NAK. TİC. LTD. ŞTİ. Türkiye Detaylı İncele Salon: 2 Stant: 253B",
            "AKANLAR ÇİKOLATA İÇECEK GIDA SAN. VE NAK. TİC. LTD. ŞTİ.",
        ),
        (
            "AL ALATAY GAYRİMENKUL GELİŞTİRME YATIRIM Türkiye Detaylı İncele Salon: 4 Stant: 435A",
            "ALATAY GAYRİMENKUL GELİŞTİRME YATIRIM",
        ),
        (
            "AN ANAKO YUMURTA VE ÜRÜNLERİ GIDA SANAYİ A.Ş. Türkiye Detaylı İncele Salon: 7 Stant: 793A",
            "ANAKO YUMURTA VE ÜRÜNLERİ GIDA SANAYİ A.Ş.",
        ),
        (
            "BA BAĞCIOĞLU BAHARAT GIDA KURUYEMİŞ Türkiye Detaylı İncele Salon: 7 Stant: 738B",
            "BAĞCIOĞLU BAHARAT GIDA KURUYEMİŞ",
        ),
        (
            "ÖZ ÖZDEN ÇİKOLATA SAN. TİC. LTD. ŞTİ. Türkiye Detaylı İncele Salon: 3 Stant: 301",
            "ÖZDEN ÇİKOLATA SAN. TİC. LTD. ŞTİ.",
        ),
        (
            "TA TAFE GIDA SAN. VE TİC. LTD. ŞTİ. Türkiye Detaylı İncele Salon: 8 Stant: 801",
            "TAFE GIDA SAN. VE TİC. LTD. ŞTİ.",
        ),
    ],
)
def test_foodist_parser_strips_logo_placeholder_prefixes(raw_prefix_text, expected_company_name):
    parsed = parse_foodist_list_text(raw_prefix_text)

    assert parsed is not None
    assert parsed.company_name == expected_company_name


@pytest.mark.parametrize(
    ("raw_text", "expected_company_name"),
    [
        (
            "A.AKSULAR GIDA TİC.VE SAN. A.Ş. Türkiye Detaylı İncele Salon: 8 Stant: 835",
            "A.AKSULAR GIDA TİC.VE SAN. A.Ş.",
        ),
        (
            "2A AKÜZÜM OTOMOTİV A.Ş. Türkiye Detaylı İncele Salon: 12 Stant: 1232A",
            "2A AKÜZÜM OTOMOTİV A.Ş.",
        ),
        (
            "44 BEYDAĞ PEYNİRCİLİK GIDA SANAYİ TİC. A.Ş. Türkiye Detaylı İncele Salon: 8 Stant: 819B",
            "44 BEYDAĞ PEYNİRCİLİK GIDA SANAYİ TİC. A.Ş.",
        ),
    ],
)
def test_foodist_parser_preserves_real_company_name_prefixes(raw_text, expected_company_name):
    parsed = parse_foodist_list_text(raw_text)

    assert parsed is not None
    assert parsed.company_name == expected_company_name


"""Tests for UMCRM SQL parser contact slot classification."""

from __future__ import annotations

import sys
from pathlib import Path

LEGACY_DIR = Path(__file__).resolve().parents[1]
if str(LEGACY_DIR) not in sys.path:
    sys.path.insert(0, str(LEGACY_DIR))

from umcrm_cleaning import parse_company_contact_slots  # noqa: E402
from umcrm_sql_parser import load_umcrm_dump  # noqa: E402


def test_new_schema_food_sector_row():
    phones, websites, emails, country = parse_company_contact_slots(
        "Türkiye",
        "",
        "3423379340",
        "oncusalca.com.tr",
        None,
    )
    assert country == "Türkiye"
    assert phones == ["3423379340"]
    assert websites == ["oncusalca.com.tr"]
    assert emails == []


def test_old_schema_phone_columns():
    phones, websites, emails, country = parse_company_contact_slots(
        "8508000294",
        None,
        "2322576940",
        None,
        None,
    )
    assert country is None
    assert phones == ["8508000294", "2322576940"]
    assert websites == []
    assert emails == []


def test_website_with_https_and_country():
    phones, websites, emails, country = parse_company_contact_slots(
        "Türkiye",
        "",
        "2126400808",
        "https://4kaglobal.com/",
        None,
    )
    assert country == "Türkiye"
    assert phones == ["2126400808"]
    assert websites == ["https://4kaglobal.com/"]
    assert emails == []


def test_acemoglu_from_sql_dump(tmp_path):
    sql = tmp_path / "sample.sql"
    sql.write_text(
        "INSERT INTO `company` VALUES "
        "('18486', 'ACEMOĞLU GIDA SANAYI VE TICARET LTD. ŞTI.', "
        "'Türkiye', '', '3423379340', 'oncusalca.com.tr', null, '1', '1', null);\n",
        encoding="utf-8",
    )
    data = load_umcrm_dump(sql)
    company = data["companies"][18486]
    assert company.phone1 == "3423379340"
    assert company.web1 == "oncusalca.com.tr"
    assert company.phone2 is None
    assert company.country_text == "Türkiye"

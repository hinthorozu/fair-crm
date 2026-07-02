"""Unit tests for UMCRM cleaning helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

LEGACY_DIR = Path(__file__).resolve().parents[1]
if str(LEGACY_DIR) not in sys.path:
    sys.path.insert(0, str(LEGACY_DIR))

from umcrm_cleaning import (  # noqa: E402
    clean_company_emails,
    clean_company_name,
    clean_company_phones,
    clean_company_websites,
    clean_fair_date,
    clean_fair_relations,
    decode_html_entities,
    sanitize_email_raw,
)


def test_email_normalize_lowercase():
    cleaned, originals, issues, stats = clean_company_emails(["Info@Example.COM"])
    assert cleaned == ["info@example.com"]
    assert originals == ["Info@Example.COM"]
    assert stats["dropped_invalid"] == 0


def test_invalid_email_drop():
    cleaned, _, issues, stats = clean_company_emails(["not-an-email", "also bad"])
    assert cleaned == []
    assert stats["dropped_invalid"] == 2
    assert any("dropped_invalid_email" in i for i in issues)


def test_placeholder_email_drop():
    cleaned, _, issues, stats = clean_company_emails(["noemail", "test@test.com"])
    assert cleaned == []
    assert stats["dropped_placeholder"] == 2
    assert any("dropped_placeholder_email" in i for i in issues)


def test_same_company_duplicate_email_merge():
    cleaned, _, issues, stats = clean_company_emails(
        ["info@example.com", "INFO@EXAMPLE.COM", "info@example.com"]
    )
    assert cleaned == ["info@example.com"]
    assert stats["duplicate_merged"] == 2


def test_cross_company_duplicate_email_kept_with_issue():
    cross = {"shared@example.com"}
    cleaned, _, issues, _ = clean_company_emails(["shared@example.com"], cross)
    assert cleaned == ["shared@example.com"]
    assert any("cross_company_duplicate_email" in i for i in issues)


def test_placeholder_phone_drop():
    phones, issues, stats = clean_company_phones("000000", "123456", None)
    assert phones == []
    assert stats["dropped_placeholder"] == 2


def test_phone_with_letters_kept_for_manual_review():
    phones, issues, _ = clean_company_phones("0532 abc def", None, None)
    assert phones == ["0532 abc def"]
    assert "phone_contains_letters" in issues
    assert "manual_review_phone" in issues


def test_website_scheme_add():
    sites, issues, stats = clean_company_websites("acme-corp.com", None)
    assert sites == ["https://acme-corp.com"]
    assert stats["normalized"] == 1
    assert any("website_scheme_added" in i for i in issues)


def test_invalid_website_dropped():
    sites, issues, stats = clean_company_websites("not a valid site!!!", None)
    assert sites == []
    assert stats["dropped_invalid"] == 1


def test_fair_date_2126_nullify():
    cleaned, nullified = clean_fair_date("2126-01-01")
    assert cleaned is None
    assert nullified is True


def test_fair_date_0000_nullify():
    cleaned, nullified = clean_fair_date("0000-00-00")
    assert cleaned is None
    assert nullified is True


def test_fair_date_1970_nullify():
    cleaned, nullified = clean_fair_date("1970-01-01")
    assert cleaned is None
    assert nullified is True


def test_valid_fair_date_kept():
    cleaned, nullified = clean_fair_date("2024-03-15 00:00:00")
    assert cleaned == "2024-03-15"
    assert nullified is False


def test_duplicate_relation_drop():
    relations = [
        (1, 10, 100),
        (2, 10, 100),
        (3, 11, 101),
    ]
    cleaned, stats = clean_fair_relations(relations, {100, 101}, {10, 11})
    assert len(cleaned) == 2
    assert stats["duplicate_dropped"] == 1
    assert stats["kept"] == 2


def test_orphan_relation_dropped():
    relations = [(1, 10, 999)]
    cleaned, stats = clean_fair_relations(relations, {100}, {10})
    assert cleaned == []
    assert stats["dropped_orphan"] == 1


def test_company_name_html_decode():
    name, issues, manual = clean_company_name("ACME &amp; CO")
    assert name == "ACME & CO"
    assert "html_entity_decoded" in issues
    assert manual is False


def test_company_placeholder_manual_review_not_dropped():
    name, issues, manual = clean_company_name("test")
    assert name == "test"
    assert "placeholder_name" in issues
    assert manual is True


def test_sanitize_email_strips_spaces():
    assert sanitize_email_raw(" info @ example.com ") == "info@example.com"

"""Shared email normalization tests."""

import pytest

from app.shared.email import is_valid_email_address, normalize_email_field


def test_single_email():
    assert normalize_email_field("info@abc.com") == "info@abc.com"


def test_multiple_emails_semicolon():
    assert normalize_email_field("info@abc.com;sales@abc.com") == "info@abc.com;sales@abc.com"


def test_multiple_emails_with_spaces():
    assert (
        normalize_email_field("info@abc.com; sales@abc.com ; export@abc.com")
        == "info@abc.com;sales@abc.com;export@abc.com"
    )


def test_comma_separator():
    assert normalize_email_field("info@abc.com, sales@abc.com") == "info@abc.com;sales@abc.com"


def test_mixed_separators_and_duplicates():
    assert (
        normalize_email_field("info@abc.com ; sales@abc.com, info@abc.com , export@abc.com")
        == "info@abc.com;sales@abc.com;export@abc.com"
    )


def test_empty_and_whitespace_only():
    assert normalize_email_field("") is None
    assert normalize_email_field("   ") is None
    assert normalize_email_field(None) is None


def test_invalid_email_raises_with_address():
    with pytest.raises(ValueError, match="Invalid email address: sales@@abc.com"):
        normalize_email_field("info@abc.com;sales@@abc.com")


def test_is_valid_email_address():
    assert is_valid_email_address("info@abc.com") is True
    assert is_valid_email_address("sales@@abc.com") is False

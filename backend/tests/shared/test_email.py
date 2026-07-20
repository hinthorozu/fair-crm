"""Shared email normalization and validation tests."""

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


@pytest.mark.parametrize(
    "email",
    [
        "abc @.oxom",
        "abc@.com",
        "abc@domain",
        "abc domain@example.com",
        "@domain.com",
        "abc@",
        "abc..def@domain.com",
        "abc@domain..com",
    ],
)
def test_is_valid_email_address_rejects_invalid(email: str):
    assert is_valid_email_address(email) is False
    with pytest.raises(ValueError, match="Invalid email address"):
        normalize_email_field(email)


@pytest.mark.parametrize(
    "email",
    [
        "abc@example.com",
        "info@firma.com.tr",
        "ad.soyad+etiket@example.co.uk",
    ],
)
def test_is_valid_email_address_accepts_valid(email: str):
    assert is_valid_email_address(email) is True


def test_internal_space_is_not_normalized_away():
    """Do not strip internal spaces to coerce validity."""
    with pytest.raises(ValueError, match=r"Invalid email address: abc @\.oxom"):
        normalize_email_field("abc @.oxom")

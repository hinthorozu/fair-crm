"""Shared email normalization and validation tests."""

import pytest

from app.shared.email import (
    is_valid_email_address,
    normalize_bulk_recipient_email,
    normalize_email_field,
)


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


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Üinfo@example.com", "uinfo@example.com"),
        ("Şinfo@example.com", "sinfo@example.com"),
        ("Ğinfo@example.com", "ginfo@example.com"),
        ("Çinfo@example.com", "cinfo@example.com"),
        ("Öinfo@example.com", "oinfo@example.com"),
        ("Iinfo@example.com", "iinfo@example.com"),
        ("BİLGİ@EXAMPLE.COM", "bilgi@example.com"),
        ("  ÜInfo@Example.COM  ", "uinfo@example.com"),
    ],
)
def test_normalize_bulk_recipient_email_turkish_chars(raw: str, expected: str):
    assert normalize_bulk_recipient_email(raw) == expected
    assert "\u0307" not in normalize_bulk_recipient_email(raw)


def test_normalize_bulk_recipient_email_dotted_capital_i_is_ascii_i():
    result = normalize_bulk_recipient_email("BİLGİ@EXAMPLE.COM")
    assert result == "bilgi@example.com"
    assert all(ord(ch) < 128 for ch in result)


def test_normalize_bulk_recipient_email_collapses_i_plus_combining_dot():
    """ASCII i + U+0307 (COMBINING DOT ABOVE) → ASCII i only."""
    raw = "si\u0307nan@umaay.com"
    result = normalize_bulk_recipient_email(raw)
    assert result == "sinan@umaay.com"
    assert "\u0307" not in result
    assert all(ord(ch) < 128 for ch in result)


def test_normalize_bulk_recipient_email_does_not_special_case_dotless_i():
    # ı must stay ı (only general lower applies; no extra map).
    assert "ı" in normalize_bulk_recipient_email("ıinfo@example.com")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("mailto:info@test-firma.com?subject=abc", "info@test-firma.com"),
        ("info@test-firma.com?body=hello", "info@test-firma.com"),
        ("info@test-firma.com#contact", "info@test-firma.com"),
        ('info@test-firma.com">', "info@test-firma.com"),
        ("info@test-firma.com</a>", "info@test-firma.com"),
        ("info@test-firma.com><i class=x", "info@test-firma.com"),
        ("daymoonpublishing@gmail.com><i class=", "daymoonpublishing@gmail.com"),
        ("info@kopernikkitap.com.tr?subject=kopernik%20kitap", "info@kopernikkitap.com.tr"),
    ],
)
def test_sanitize_scraped_email_prefers_normalized(raw: str, expected: str):
    from app.shared.email import sanitize_scraped_email

    assert sanitize_scraped_email(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "bilinci.@necati.balbay",
        "abc@",
        "@abc.com",
        "abc..def@test-firma.com",
        "test@@mail.com",
        ".abc@test-firma.com",
        "abc.@test-firma.com",
        "",
        None,
    ],
)
def test_sanitize_scraped_email_rejects_invalid(raw: str | None):
    from app.shared.email import sanitize_scraped_email

    assert sanitize_scraped_email(raw) is None


def test_cut_email_at_invalid_chars():
    from app.shared.email import cut_email_at_invalid_chars

    assert cut_email_at_invalid_chars("info@a.com><i") == "info@a.com"
    assert cut_email_at_invalid_chars("a@b.com?x") == "a@b.com"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("info[at]firma.com", "info@firma.com"),
        ("info [at] company [dot] com", "info@company.com"),
        ("mailto:info@test-firma.com?subject=abc", "info@test-firma.com"),
        ("info@test-firma.com;sales@test-firma.com", "info@test-firma.com;sales@test-firma.com"),
        ("info@test-firma.com;not-an-email", "info@test-firma.com"),
        ("not-an-email", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_email_candidates_uses_sanitize_pipeline(raw: str | None, expected: str | None):
    from app.shared.email import normalize_email_candidates

    assert normalize_email_candidates(raw) == expected


def test_normalize_email_field_sanitizes_dirty_token():
    assert (
        normalize_email_field("info@test-firma.com?subject=x;sales@test-firma.com")
        == "info@test-firma.com;sales@test-firma.com"
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("info[at]firma.com", "info@firma.com"),
        ("info(at)firma.com", "info@firma.com"),
        ("info (at) firma.com", "info@firma.com"),
        ("info {at} firma.com", "info@firma.com"),
        ("info [AT] firma.com", "info@firma.com"),
        ("info [dot] firma.com", None),  # no @ after deobfuscation → invalid
        ("info(dot)firma.com", None),
        ("info {dot} firma.com", None),
        ("info [at] company [dot] com", "info@company.com"),
        ("info[at]company[dot]com", "info@company.com"),
        ("INFO (At) Company (DOT) COM", "info@company.com"),
        ("sales{at}ornek{dot}com{dot}tr", "sales@ornek.com.tr"),
    ],
)
def test_sanitize_scraped_email_deobfuscates_at_dot(raw: str, expected: str | None):
    from app.shared.email import sanitize_scraped_email

    assert sanitize_scraped_email(raw) == expected


def test_deobfuscate_email_text_collapses_spaces_and_is_case_insensitive():
    from app.shared.email import deobfuscate_email_text

    assert deobfuscate_email_text("info  [AT]   firma  [DoT]  com") == "info@firma.com"
    assert deobfuscate_email_text("info [dot] firma.com") == "info.firma.com"
    assert deobfuscate_email_text("info(dot)firma.com") == "info.firma.com"
    assert deobfuscate_email_text("info {dot} firma.com") == "info.firma.com"


@pytest.mark.parametrize(
    "email",
    [
        "bilinci.@necati.balbay",
        "test@@mail.com",
        ".abc@test.com",
        "abc.@test.com",
    ],
)
def test_additional_invalid_shapes_rejected(email: str):
    assert is_valid_email_address(email) is False
    with pytest.raises(ValueError, match="Invalid email address"):
        normalize_email_field(email)

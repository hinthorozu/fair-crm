"""Unit tests for manual/Excel recipient resolution used by ops bulk-email preview."""

import pytest

from app.modules.fair_emails.application.recipient_resolution import resolve_manual_and_excel_emails


def test_resolve_manual_and_excel_merges_dedupes_and_skips_invalid():
    result = resolve_manual_and_excel_emails(
        manual_emails_text="a@example.com; bad-email ; a@example.com",
        excel_email_tokens=["b@example.com", "a@example.com", "also-bad"],
    )
    assert result.total_found == 6
    assert result.valid_email_count == 2
    assert result.duplicate_count == 2
    assert result.invalid_count == 2
    assert result.deduped_recipient_count == 2
    will_send = [item for item in result.recipients if item.status == "will_send"]
    assert {item.email for item in will_send} == {"a@example.com", "b@example.com"}
    assert will_send[0].source == "manual"
    assert will_send[1].source == "excel"


def test_resolve_manual_only():
    result = resolve_manual_and_excel_emails(
        manual_emails_text="one@x.com; two@y.com",
        excel_email_tokens=[],
    )
    assert result.total_found == 2
    assert result.deduped_recipient_count == 2
    assert result.invalid_count == 0
    assert result.duplicate_count == 0


def test_resolve_manual_valid_invalid_valid_pattern():
    result = resolve_manual_and_excel_emails(
        manual_emails_text="valid@example.com; bad-email; second@example.com",
        excel_email_tokens=[],
    )
    assert result.total_found == 3
    assert result.valid_email_count == 2
    assert result.invalid_count == 1
    assert result.duplicate_count == 0
    assert result.deduped_recipient_count == 2
    by_email = {item.email: item for item in result.recipients}
    assert by_email["valid@example.com"].status == "will_send"
    assert by_email["second@example.com"].status == "will_send"
    assert by_email["bad-email"].status == "skip"
    assert by_email["bad-email"].skip_reason == "invalid_email"


def test_resolve_manual_whitespace_normalized_as_valid():
    result = resolve_manual_and_excel_emails(
        manual_emails_text="  valid@example.com  ",
        excel_email_tokens=[],
    )
    assert result.total_found == 1
    assert result.valid_email_count == 1
    assert result.invalid_count == 0
    assert result.recipients[0].status == "will_send"
    assert result.recipients[0].email == "valid@example.com"


def test_resolve_manual_invalid_plus_duplicate_counts():
    """4 tokens: 2 unique valid, 1 duplicate of a valid, 1 invalid."""
    result = resolve_manual_and_excel_emails(
        manual_emails_text="one@example.com; bad; two@example.com; one@example.com",
        excel_email_tokens=[],
    )
    assert result.total_found == 4
    assert result.valid_email_count == 2
    assert result.duplicate_count == 1
    assert result.invalid_count == 1
    assert result.deduped_recipient_count == 2
    assert result.skipped_count == 2


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
    ],
)
def test_resolve_manual_turkish_char_normalization(raw: str, expected: str):
    result = resolve_manual_and_excel_emails(
        manual_emails_text=raw,
        excel_email_tokens=[],
    )
    assert result.deduped_recipient_count == 1
    assert result.recipients[0].status == "will_send"
    assert result.recipients[0].email == expected
    assert result.recipients[0].source == "manual"


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
    ],
)
def test_resolve_excel_turkish_char_normalization(raw: str, expected: str):
    result = resolve_manual_and_excel_emails(
        manual_emails_text=None,
        excel_email_tokens=[raw],
    )
    assert result.deduped_recipient_count == 1
    assert result.recipients[0].status == "will_send"
    assert result.recipients[0].email == expected
    assert result.recipients[0].source == "excel"


def test_resolve_manual_and_excel_dedupe_after_turkish_normalization():
    result = resolve_manual_and_excel_emails(
        manual_emails_text="Üinfo@example.com",
        excel_email_tokens=["uinfo@example.com"],
    )
    assert result.deduped_recipient_count == 1
    assert result.duplicate_count == 1
    will_send = [item for item in result.recipients if item.status == "will_send"]
    assert will_send[0].email == "uinfo@example.com"
    assert will_send[0].source == "manual"

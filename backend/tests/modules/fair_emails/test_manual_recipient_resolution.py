"""Unit tests for manual/Excel recipient resolution used by ops bulk-email preview."""

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

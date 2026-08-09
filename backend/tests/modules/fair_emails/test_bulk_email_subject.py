from app.modules.fair_emails.application.subject import build_bulk_email_subject


def test_bulk_email_subject_prefixes_fair_name() -> None:
    assert build_bulk_email_subject("Stand teklifi", "Metal Expo 2026") == (
        "Metal Expo 2026 - Stand teklifi"
    )


def test_bulk_email_subject_stays_unchanged_without_fair() -> None:
    assert build_bulk_email_subject("Stand teklifi", None) == "Stand teklifi"
    assert build_bulk_email_subject("Stand teklifi", "  ") == "Stand teklifi"


def test_bulk_email_subject_normalizes_outer_whitespace() -> None:
    assert build_bulk_email_subject("  Stand teklifi  ", "  Metal Expo 2026  ") == (
        "Metal Expo 2026 - Stand teklifi"
    )


def test_bulk_email_subject_does_not_duplicate_existing_fair_prefix() -> None:
    assert build_bulk_email_subject(
        "Metal Expo 2026 - Stand teklifi",
        "Metal Expo 2026",
    ) == "Metal Expo 2026 - Stand teklifi"

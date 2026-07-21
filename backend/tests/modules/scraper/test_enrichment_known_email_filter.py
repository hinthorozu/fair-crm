"""Tests for stripping CRM-known emails from enrichment results."""

from uuid import uuid4

from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto, SourcedValue
from app.modules.scraper.services.enrichment_known_email_filter import (
    filter_known_crm_emails_from_result,
)


def _result(*, emails: list[str], phones: list[str] | None = None) -> EnrichmentResultDto:
    return EnrichmentResultDto(
        customer_id=uuid4(),
        company_name="Filter Co",
        website="https://filter.test",
        emails=[SourcedValue(value=email, source_url="https://filter.test") for email in emails],
        phones=[SourcedValue(value=phone, source_url="https://filter.test") for phone in (phones or [])],
        status="found",
    )


def test_filter_keeps_novel_emails_and_drops_known():
    filtered = filter_known_crm_emails_from_result(
        _result(emails=["info@filter.test", "sales@filter.test", "Info@Filter.Test"]),
        {"info@filter.test"},
    )
    assert filtered.status == "found"
    assert [item.value for item in filtered.emails] == ["sales@filter.test"]


def test_filter_marks_duplicate_only_as_skipped():
    filtered = filter_known_crm_emails_from_result(
        _result(emails=["info@filter.test", "INFO@filter.test"]),
        {"info@filter.test"},
    )
    assert filtered.status == "skipped"
    assert filtered.emails == []
    assert filtered.error == "duplicate_email_only"


def test_filter_keeps_found_when_only_phone_remains_after_email_dedupe():
    filtered = filter_known_crm_emails_from_result(
        _result(emails=["info@filter.test"], phones=["+905551112233"]),
        {"info@filter.test"},
    )
    assert filtered.status == "found"
    assert filtered.emails == []
    assert len(filtered.phones) == 1

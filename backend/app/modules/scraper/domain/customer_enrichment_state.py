"""Persistent scan state for customer contact enrichment."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum


class CustomerEnrichmentScanStatus(StrEnum):
    NOT_SCANNED = "not_scanned"
    EMAIL_FOUND = "email_found"
    EMAIL_NOT_FOUND = "email_not_found"
    FAILED = "failed"
    PENDING_MERGE = "pending_merge"
    SKIPPED_EMAIL_EXISTS = "skipped_email_exists"
    SKIPPED_NO_WEBSITE = "skipped_no_website"


EMAIL_NOT_FOUND_RETRY = timedelta(days=30)
FAILED_RETRY = timedelta(days=7)

# pending_merge is informational only ("import awaiting") — scan is not complete until
# import/merge writes CRM data (then status becomes email_found). It must not block
# re-selection as an enrichment candidate.
BLOCKING_STATUSES = frozenset(
    {
        CustomerEnrichmentScanStatus.EMAIL_FOUND,
        CustomerEnrichmentScanStatus.SKIPPED_EMAIL_EXISTS,
        CustomerEnrichmentScanStatus.SKIPPED_NO_WEBSITE,
    }
)

RETRYABLE_STATUSES = frozenset(
    {
        CustomerEnrichmentScanStatus.EMAIL_NOT_FOUND,
        CustomerEnrichmentScanStatus.FAILED,
    }
)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def is_eligible_for_enrichment_scan(
    *,
    status: str | None,
    retry_after: datetime | None,
    website_changed: bool,
    now: datetime | None = None,
) -> bool:
    if website_changed:
        return True
    if status is None or status == CustomerEnrichmentScanStatus.NOT_SCANNED:
        return True
    # Import not applied yet — still eligible for the same filter / re-run.
    if status == CustomerEnrichmentScanStatus.PENDING_MERGE:
        return True
    if status in BLOCKING_STATUSES:
        return False
    if status in RETRYABLE_STATUSES:
        if retry_after is None:
            return True
        current = _ensure_utc(now or datetime.now(tz=UTC))
        return current >= _ensure_utc(retry_after)
    return False

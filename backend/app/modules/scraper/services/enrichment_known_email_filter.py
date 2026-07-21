"""Drop CRM-known emails from enrichment results before import handoff."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.customers.infrastructure.persistence.communication_models import CustomerEmailModel
from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto, SourcedValue


def _normalize_email_key(value: str) -> str | None:
    """Normalize for duplicate comparison only (lowercase + trim).

    Avoids deliverability/TLD validation so crawl hits still match CRM rows.
    """
    text = (value or "").strip().lower()
    return text or None


def load_customer_email_keys(
    session: Session,
    *,
    organization_id: UUID,
    customer_ids: list[UUID],
) -> dict[UUID, set[str]]:
    if not customer_ids:
        return {}
    rows = (
        session.query(CustomerEmailModel.customer_id, CustomerEmailModel.email)
        .filter(
            CustomerEmailModel.organization_id == organization_id,
            CustomerEmailModel.customer_id.in_(customer_ids),
        )
        .all()
    )
    known: dict[UUID, set[str]] = {customer_id: set() for customer_id in customer_ids}
    for customer_id, email in rows:
        key = _normalize_email_key(email or "")
        if key is None:
            continue
        known.setdefault(customer_id, set()).add(key)
    return known


def _has_non_email_payload(result: EnrichmentResultDto) -> bool:
    if result.phones:
        return True
    if result.address is not None:
        return True
    return any(value is not None for value in (result.social_links or {}).values())


def filter_known_crm_emails_from_result(
    result: EnrichmentResultDto,
    known_emails: set[str],
) -> EnrichmentResultDto:
    """Return a copy whose emails exclude addresses already on the CRM customer.

    When the crawl found emails but every address is already stored, status becomes
    ``skipped`` so scan bookkeeping does not apply an email_not_found cooldown and
    import handoff creates no row (no new CRM data).
    """
    if result.status in ("failed", "skipped") or not result.emails:
        return result

    novel: list[SourcedValue] = []
    duplicate_count = 0
    for item in result.emails:
        key = _normalize_email_key(item.value)
        if key is None:
            continue
        if key in known_emails:
            duplicate_count += 1
            continue
        novel.append(item)

    if duplicate_count == 0 and len(novel) == len(result.emails):
        return result

    if novel or _has_non_email_payload(result):
        return EnrichmentResultDto(
            customer_id=result.customer_id,
            company_name=result.company_name,
            website=result.website,
            emails=novel,
            phones=result.phones,
            address=result.address,
            social_links=result.social_links,
            status="found",
            error=result.error,
        )

    if duplicate_count > 0:
        return EnrichmentResultDto(
            customer_id=result.customer_id,
            company_name=result.company_name,
            website=result.website,
            emails=[],
            phones=result.phones,
            address=result.address,
            social_links=result.social_links,
            status="skipped",
            error="duplicate_email_only",
        )

    return result


def filter_known_crm_emails_from_results(
    session: Session,
    *,
    organization_id: UUID,
    results: list[EnrichmentResultDto],
) -> list[EnrichmentResultDto]:
    known_by_customer = load_customer_email_keys(
        session,
        organization_id=organization_id,
        customer_ids=[result.customer_id for result in results],
    )
    return [
        filter_known_crm_emails_from_result(
            result,
            known_by_customer.get(result.customer_id, set()),
        )
        for result in results
    ]

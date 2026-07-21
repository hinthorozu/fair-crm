"""Persist and query customer contact enrichment scan state."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.imports.application.batch_display_metadata import resolve_adapter_key_from_batch
from app.modules.imports.domain.entities import ImportBatch
from app.modules.scraper.domain.enrichment_adapter import is_customer_contact_enrichment_adapter
from app.modules.scraper.domain.customer_enrichment_state import (
    EMAIL_NOT_FOUND_RETRY,
    FAILED_RETRY,
    CustomerEnrichmentScanStatus,
    is_eligible_for_enrichment_scan,
)
from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto
from app.modules.scraper.infrastructure.persistence.models import CustomerEnrichmentStateModel


def _now() -> datetime:
    return datetime.now(tz=UTC)


def is_enrichment_import_batch(batch: ImportBatch) -> bool:
    return is_customer_contact_enrichment_adapter(resolve_adapter_key_from_batch(batch))


def load_state_map(
    session: Session,
    organization_id: UUID,
    customer_ids: list[UUID],
) -> dict[UUID, CustomerEnrichmentStateModel]:
    if not customer_ids:
        return {}
    rows = (
        session.query(CustomerEnrichmentStateModel)
        .filter(
            CustomerEnrichmentStateModel.organization_id == organization_id,
            CustomerEnrichmentStateModel.customer_id.in_(customer_ids),
        )
        .all()
    )
    return {row.customer_id: row for row in rows}


def _get_or_create_state(
    session: Session,
    *,
    organization_id: UUID,
    customer_id: UUID,
) -> CustomerEnrichmentStateModel:
    row = (
        session.query(CustomerEnrichmentStateModel)
        .filter(
            CustomerEnrichmentStateModel.organization_id == organization_id,
            CustomerEnrichmentStateModel.customer_id == customer_id,
        )
        .one_or_none()
    )
    if row is not None:
        return row
    now = _now()
    row = CustomerEnrichmentStateModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=customer_id,
        website=None,
        last_enrichment_run_id=None,
        last_email_scan_at=None,
        last_email_scan_status=CustomerEnrichmentScanStatus.NOT_SCANNED,
        last_email_found=None,
        last_source_url=None,
        last_error=None,
        retry_after=None,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    return row


def mark_skipped_email_exists(
    session: Session,
    *,
    organization_id: UUID,
    customer_id: UUID,
    website: str | None,
) -> None:
    row = _get_or_create_state(session, organization_id=organization_id, customer_id=customer_id)
    now = _now()
    row.website = website
    row.last_email_scan_status = CustomerEnrichmentScanStatus.SKIPPED_EMAIL_EXISTS
    row.last_email_found = None
    row.last_source_url = None
    row.last_error = None
    row.retry_after = None
    row.updated_at = now


def is_customer_scan_eligible(
    state: CustomerEnrichmentStateModel | None,
    *,
    website: str,
) -> bool:
    normalized_website = website.strip()
    website_changed = state is not None and (state.website or "").strip() != normalized_website
    status = state.last_email_scan_status if state is not None else None
    retry_after = state.retry_after if state is not None else None
    return is_eligible_for_enrichment_scan(
        status=status,
        retry_after=retry_after,
        website_changed=website_changed,
    )


def record_scan_result(
    session: Session,
    *,
    organization_id: UUID,
    run_id: UUID,
    result: EnrichmentResultDto,
) -> None:
    row = _get_or_create_state(
        session,
        organization_id=organization_id,
        customer_id=result.customer_id,
    )
    now = _now()
    row.website = result.website
    row.last_enrichment_run_id = run_id
    row.last_email_scan_at = now
    row.updated_at = now

    if result.status == "failed":
        row.last_email_scan_status = CustomerEnrichmentScanStatus.FAILED
        row.last_email_found = None
        row.last_source_url = None
        row.last_error = result.error
        row.retry_after = now + FAILED_RETRY
        return

    first_email = result.emails[0] if result.emails else None
    if first_email is not None:
        # Persist scan evidence only. EMAIL_FOUND is reserved for post-import apply
        # (CRM write). Batch creation moves these rows to PENDING_MERGE; if no batch
        # is created the customer stays non-blocking and can be re-scanned.
        row.last_email_found = first_email.value
        row.last_source_url = first_email.source_url
        row.last_error = None
        row.retry_after = None
        if row.last_email_scan_status != CustomerEnrichmentScanStatus.PENDING_MERGE:
            row.last_email_scan_status = CustomerEnrichmentScanStatus.NOT_SCANNED
        return

    source_url = result.phones[0].source_url if result.phones else result.website
    row.last_email_scan_status = CustomerEnrichmentScanStatus.EMAIL_NOT_FOUND
    row.last_email_found = None
    row.last_source_url = source_url
    row.last_error = None
    row.retry_after = now + EMAIL_NOT_FOUND_RETRY


def mark_customers_pending_merge(
    session: Session,
    *,
    organization_id: UUID,
    run_id: UUID,
    customer_ids: list[UUID],
) -> None:
    if not customer_ids:
        return
    now = _now()
    for customer_id in customer_ids:
        row = (
            session.query(CustomerEnrichmentStateModel)
            .filter(
                CustomerEnrichmentStateModel.organization_id == organization_id,
                CustomerEnrichmentStateModel.customer_id == customer_id,
            )
            .one_or_none()
        )
        if row is None:
            continue
        row.last_enrichment_run_id = run_id
        row.last_email_scan_status = CustomerEnrichmentScanStatus.PENDING_MERGE
        row.retry_after = None
        row.updated_at = now


def record_enrichment_apply_outcome(
    session: Session,
    *,
    organization_id: UUID,
    customer_id: UUID,
    had_email_before: bool = False,
    email_written: bool = False,
    crm_data_written: bool | None = None,
) -> None:
    """Transition pending_merge → email_found only when CRM gained new enrichment data.

    ``email_found`` means enriched (new data applied to the customer card), not merely
    scanned or duplicate-confirmed. Duplicate email with no new fields keeps pending_merge.

    ``crm_data_written`` is preferred when the caller can detect email/phone/address/social
    writes. When omitted, ``email_written`` is used (email-only detection).
    ``had_email_before`` is retained for call-site compatibility and is not used for status.
    """
    del had_email_before  # call-site compat; does not imply enrichment completed
    row = (
        session.query(CustomerEnrichmentStateModel)
        .filter(
            CustomerEnrichmentStateModel.organization_id == organization_id,
            CustomerEnrichmentStateModel.customer_id == customer_id,
        )
        .one_or_none()
    )
    if row is None:
        return
    if row.last_email_scan_status != CustomerEnrichmentScanStatus.PENDING_MERGE:
        return

    now = _now()
    row.updated_at = now
    row.retry_after = None
    row.last_error = None

    written = email_written if crm_data_written is None else crm_data_written
    if written:
        row.last_email_scan_status = CustomerEnrichmentScanStatus.EMAIL_FOUND


def clear_blocking_states_for_cancelled_run(
    session: Session,
    *,
    organization_id: UUID,
    run_id: UUID,
) -> int:
    """Drop failed/email_not_found cooldowns written during a user-cancelled run.

    Import/merge did not complete; user stop must not shrink the candidate pool.
    ``pending_merge`` / ``email_found`` rows for this run are left unchanged.
    """
    rows = (
        session.query(CustomerEnrichmentStateModel)
        .filter(
            CustomerEnrichmentStateModel.organization_id == organization_id,
            CustomerEnrichmentStateModel.last_enrichment_run_id == run_id,
            CustomerEnrichmentStateModel.last_email_scan_status.in_(
                (
                    CustomerEnrichmentScanStatus.FAILED.value,
                    CustomerEnrichmentScanStatus.EMAIL_NOT_FOUND.value,
                )
            ),
        )
        .all()
    )
    if not rows:
        return 0
    now = _now()
    for row in rows:
        row.last_email_scan_status = CustomerEnrichmentScanStatus.NOT_SCANNED
        row.retry_after = None
        row.last_error = None
        row.updated_at = now
    return len(rows)


def reset_enrichment_states(
    session: Session,
    *,
    organization_id: UUID,
    customer_ids: list[UUID] | None = None,
) -> int:
    query = session.query(CustomerEnrichmentStateModel).filter(
        CustomerEnrichmentStateModel.organization_id == organization_id,
    )
    if customer_ids:
        query = query.filter(CustomerEnrichmentStateModel.customer_id.in_(customer_ids))
    deleted = query.delete(synchronize_session=False)
    return int(deleted or 0)


def count_active_customer_emails(
    session: Session,
    *,
    organization_id: UUID,
    customer_id: UUID,
) -> int:
    from app.modules.customers.infrastructure.persistence.communication_models import CustomerEmailModel

    return (
        session.query(CustomerEmailModel.id)
        .filter(
            CustomerEmailModel.organization_id == organization_id,
            CustomerEmailModel.customer_id == customer_id,
        )
        .count()
    )


def reset_enrichment_state_if_customer_has_no_email(
    session: Session,
    *,
    organization_id: UUID,
    customer_id: UUID,
) -> int:
    """Clear enrichment state when a customer has no remaining CRM emails."""
    if count_active_customer_emails(session, organization_id=organization_id, customer_id=customer_id) > 0:
        return 0
    return reset_enrichment_states(
        session,
        organization_id=organization_id,
        customer_ids=[customer_id],
    )


def customer_ids_from_handoff_metadata(row_metadata: list[dict] | None) -> list[UUID]:
    ids: list[UUID] = []
    seen: set[UUID] = set()
    for meta in row_metadata or []:
        raw_id = meta.get("customer_id") or meta.get("external_id")
        if raw_id is None:
            continue
        try:
            customer_id = UUID(str(raw_id))
        except ValueError:
            continue
        if customer_id in seen:
            continue
        seen.add(customer_id)
        ids.append(customer_id)
    return ids

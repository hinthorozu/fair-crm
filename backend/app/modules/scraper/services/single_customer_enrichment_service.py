"""Single-customer contact enrichment validation, state view, and candidates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.scraper.domain.customer_enrichment_state import CustomerEnrichmentScanStatus
from app.modules.scraper.services.customer_enrichment_state_service import (
    is_customer_scan_eligible,
    load_state_map,
)
from app.modules.scraper.services.enrichment_candidate_service import EnrichmentCandidate
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.services.scraper_run_log_service import ScraperRunLogService


class SingleCustomerEnrichmentError(ValueError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CustomerContactEnrichmentStateView:
    customer_id: UUID
    status: str
    last_email_scan_at: datetime | None
    last_email_found: str | None
    last_source_url: str | None
    last_error: str | None
    retry_after: datetime | None
    last_enrichment_run_id: UUID | None
    import_batch_id: UUID | None
    can_run: bool
    block_code: str | None
    block_message: str | None
    website: str | None
    has_crm_email: bool


def _primary_website(session: Session, organization_id: UUID, customer_id: UUID) -> str | None:
    row = (
        session.query(CustomerWebsiteModel)
        .filter(
            CustomerWebsiteModel.organization_id == organization_id,
            CustomerWebsiteModel.customer_id == customer_id,
        )
        .order_by(
            CustomerWebsiteModel.is_primary.desc(),
            CustomerWebsiteModel.created_at.asc(),
        )
        .first()
    )
    if row is None:
        return None
    website = (row.website or "").strip()
    return website or None


def _has_crm_email(session: Session, organization_id: UUID, customer_id: UUID) -> bool:
    return (
        session.query(CustomerEmailModel.id)
        .filter(
            CustomerEmailModel.organization_id == organization_id,
            CustomerEmailModel.customer_id == customer_id,
        )
        .first()
        is not None
    )


def _evaluate_run_blockers(
    *,
    website: str | None,
    state_status: str | None,
    state_map_entry,
) -> tuple[bool, str | None, str | None]:
    """Decide whether a single-customer enrichment run is allowed.

    Existing CRM emails never block the run: the scan still crawls the website to
    discover additional addresses. Duplicate handling happens later at import apply.
    """
    if not website:
        return (
            False,
            "no_website",
            "Bu müşterinin web sitesi olmadığı için zenginleştirme çalıştırılamaz.",
        )
    # pending_merge is informational (import awaiting) — does not block a re-scan.
    # Legacy "skipped because CRM email already existed" must not permanently lock
    # the card — the operator can re-scan to find additional emails without a reset.
    if state_status == CustomerEnrichmentScanStatus.SKIPPED_EMAIL_EXISTS:
        return True, None, None
    state_for_eligibility = state_map_entry if state_map_entry is not None else None
    if not is_customer_scan_eligible(state_for_eligibility, website=website):
        if state_status == CustomerEnrichmentScanStatus.EMAIL_FOUND:
            return (
                False,
                "already_enriched",
                "Bu müşteri zenginleştirildi (veri CRM'e yazıldı). Tekrar taramak için durumu sıfırlayın.",
            )
        return (
            False,
            "not_eligible",
            "Bu müşteri şu anda zenginleştirme için uygun değil. Durumu sıfırlamayı deneyin.",
        )
    return True, None, None


def get_customer_contact_enrichment_state(
    session: Session,
    *,
    organization_id: UUID,
    customer_id: UUID,
    run_history_service: ScraperRunHistoryService | None = None,
) -> CustomerContactEnrichmentStateView:
    customer = (
        session.query(CustomerModel)
        .filter(
            CustomerModel.id == customer_id,
            CustomerModel.organization_id == organization_id,
            CustomerModel.deleted_at.is_(None),
        )
        .one_or_none()
    )
    if customer is None:
        raise KeyError(f"Customer not found: {customer_id}")

    website = _primary_website(session, organization_id, customer_id)
    has_crm_email = _has_crm_email(session, organization_id, customer_id)
    state_map = load_state_map(session, organization_id, [customer_id])
    state = state_map.get(customer_id)

    status = (
        state.last_email_scan_status
        if state is not None
        else CustomerEnrichmentScanStatus.NOT_SCANNED
    )
    can_run, block_code, block_message = _evaluate_run_blockers(
        website=website,
        state_status=status if state is not None else None,
        state_map_entry=state,
    )

    import_batch_id: UUID | None = None
    last_run_id = state.last_enrichment_run_id if state is not None else None
    if last_run_id is not None and run_history_service is not None:
        run = run_history_service.get_run(last_run_id)
        if run is not None:
            import_batch_id = run.import_batch_id

    return CustomerContactEnrichmentStateView(
        customer_id=customer_id,
        status=status,
        last_email_scan_at=state.last_email_scan_at if state is not None else None,
        last_email_found=state.last_email_found if state is not None else None,
        last_source_url=state.last_source_url if state is not None else None,
        last_error=state.last_error if state is not None else None,
        retry_after=state.retry_after if state is not None else None,
        last_enrichment_run_id=last_run_id,
        import_batch_id=import_batch_id,
        can_run=can_run,
        block_code=block_code,
        block_message=block_message,
        website=website,
        has_crm_email=has_crm_email,
    )


def validate_single_customer_enrichment_run(
    session: Session,
    *,
    organization_id: UUID,
    customer_id: UUID,
    run_history_service: ScraperRunHistoryService | None = None,
) -> CustomerContactEnrichmentStateView:
    view = get_customer_contact_enrichment_state(
        session,
        organization_id=organization_id,
        customer_id=customer_id,
        run_history_service=run_history_service,
    )
    if not view.can_run:
        raise SingleCustomerEnrichmentError(
            view.block_message or "Zenginleştirme çalıştırılamaz.",
            code=view.block_code or "not_eligible",
        )
    return view


def build_enrichment_candidate_for_customer(
    session: Session,
    *,
    organization_id: UUID,
    customer_id: UUID,
) -> EnrichmentCandidate | None:
    customer = (
        session.query(CustomerModel)
        .filter(
            CustomerModel.id == customer_id,
            CustomerModel.organization_id == organization_id,
            CustomerModel.deleted_at.is_(None),
        )
        .one_or_none()
    )
    if customer is None:
        return None
    website = _primary_website(session, organization_id, customer_id)
    if not website:
        return None
    return EnrichmentCandidate(
        customer_id=customer.id,
        company_name=customer.display_name,
        website=website,
    )


def list_enrichment_candidates_for_customer_ids(
    session: Session,
    organization_id: UUID,
    customer_ids: list[UUID],
) -> list[EnrichmentCandidate]:
    candidates: list[EnrichmentCandidate] = []
    for customer_id in customer_ids:
        candidate = build_enrichment_candidate_for_customer(
            session,
            organization_id=organization_id,
            customer_id=customer_id,
        )
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def recent_run_logs_for_state(
    log_service: ScraperRunLogService,
    run_id: UUID | None,
    *,
    limit: int = 100,
):
    if run_id is None:
        return []
    return log_service.list_logs(run_id, limit=limit)

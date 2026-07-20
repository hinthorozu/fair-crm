"""Find CRM customers eligible for website contact enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, exists, func
from sqlalchemy.orm import Session

from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.scraper.services.customer_enrichment_state_service import (
    is_customer_scan_eligible,
    load_state_map,
)


@dataclass(frozen=True)
class EnrichmentCandidate:
    customer_id: UUID
    company_name: str
    website: str


def _website_has_email_subquery(organization_id: UUID):
    return exists().where(
        and_(
            CustomerEmailModel.organization_id == organization_id,
            CustomerEmailModel.customer_id == CustomerWebsiteModel.customer_id,
        )
    )


def list_enrichment_candidates(
    session: Session,
    organization_id: UUID,
    *,
    limit: int | None = None,
    fair_id: UUID | None = None,
    ignore_previous_scan_state: bool = False,
    include_existing_email: bool = False,
) -> list[EnrichmentCandidate]:
    """Return customers eligible for enrichment based on website, email, and scan state.

    ``ignore_previous_scan_state`` skips the per-customer enrichment-state check
    (pending_merge, failed/email_not_found retry cooldowns, previously completed scans)
    entirely. It is intended for a manually-triggered, single-fair scoped run, where the
    user explicitly asked to (re)scan that fair's participants and should not have to know
    about or clear prior scan bookkeeping for another run to pick them up.

    ``include_existing_email`` disables the default "no CRM email" filter so customers who
    already have an email can be re-scanned for new or updated contact data. When False
    (default), only website-holding customers without any CRM email are returned — the
    original enrichment behaviour.
    """
    filters = [
        CustomerModel.organization_id == organization_id,
        CustomerModel.deleted_at.is_(None),
        CustomerWebsiteModel.organization_id == organization_id,
        CustomerWebsiteModel.website.isnot(None),
        func.trim(CustomerWebsiteModel.website) != "",
    ]
    if not include_existing_email:
        filters.append(~_website_has_email_subquery(organization_id))

    query = (
        session.query(CustomerWebsiteModel, CustomerModel)
        .join(CustomerModel, CustomerModel.id == CustomerWebsiteModel.customer_id)
        .filter(*filters)
    )
    if fair_id is not None:
        query = query.join(
            CustomerFairParticipationModel,
            and_(
                CustomerFairParticipationModel.customer_id == CustomerModel.id,
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.fair_id == fair_id,
                CustomerFairParticipationModel.deleted_at.is_(None),
            ),
        )
    rows = (
        query
        .order_by(
            CustomerWebsiteModel.is_primary.desc(),
            CustomerWebsiteModel.created_at.asc(),
            CustomerModel.display_name.asc(),
        )
        .all()
    )

    seen_customer_ids: set[UUID] = set()
    pending: list[tuple[CustomerModel, str]] = []

    for website_model, customer in rows:
        if customer.id in seen_customer_ids:
            continue
        website = (website_model.website or "").strip()
        if not website:
            continue
        seen_customer_ids.add(customer.id)
        pending.append((customer, website))

    state_map = (
        {}
        if ignore_previous_scan_state
        else load_state_map(
            session,
            organization_id,
            [customer.id for customer, _website in pending],
        )
    )

    candidates: list[EnrichmentCandidate] = []
    for customer, website in pending:
        if not ignore_previous_scan_state:
            state = state_map.get(customer.id)
            if not is_customer_scan_eligible(state, website=website):
                continue
        candidates.append(
            EnrichmentCandidate(
                customer_id=customer.id,
                company_name=customer.display_name,
                website=website,
            )
        )
        if limit is not None and len(candidates) >= limit:
            break

    return candidates

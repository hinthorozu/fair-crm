"""Find CRM customers eligible for website contact enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import and_, exists, func, or_
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

CompanyNameMatchMode = Literal["contains", "starts_with"]


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


def _company_name_filter(company_name: str, match: CompanyNameMatchMode):
    needle = company_name.strip()
    if not needle:
        return None
    if match == "starts_with":
        return CustomerModel.display_name.ilike(f"{needle}%")
    return CustomerModel.display_name.ilike(f"%{needle}%")


def _address_contains_filter(address_contains: str):
    needle = address_contains.strip()
    if not needle:
        return None
    pattern = f"%{needle}%"
    return or_(
        CustomerModel.address.ilike(pattern),
        CustomerModel.city.ilike(pattern),
    )


def list_enrichment_candidates(
    session: Session,
    organization_id: UUID,
    *,
    limit: int | None = None,
    fair_id: UUID | None = None,
    ignore_previous_scan_state: bool = False,
    include_existing_email: bool = False,
    company_name: str | None = None,
    company_name_match: CompanyNameMatchMode = "contains",
    address_contains: str | None = None,
) -> list[EnrichmentCandidate]:
    """Return customers eligible for enrichment based on website, email, and scan state.

    ``ignore_previous_scan_state`` skips the per-customer enrichment-state check
    (failed/email_not_found retry cooldowns, email_found after import, other blocking
    statuses) entirely. ``pending_merge`` is never blocking — it only means import is
    awaiting. This flag is intended for a manually-triggered, single-fair scoped run,
    where the user explicitly asked to (re)scan that fair's participants and should not
    have to know about or clear prior scan bookkeeping for another run to pick them up.

    ``include_existing_email`` disables the default "no CRM email" filter so customers who
    already have an email can be re-scanned for new or updated contact data. When False
    (default), only website-holding customers without any CRM email are returned — the
    original enrichment behaviour.

    Optional filters (``company_name``, ``address_contains``, ``fair_id``) narrow the
    candidate pool; all are optional so a run can target a limited subset without
    requiring every filter.
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

    company_filter = _company_name_filter(company_name or "", company_name_match)
    if company_filter is not None:
        filters.append(company_filter)

    address_filter = _address_contains_filter(address_contains or "")
    if address_filter is not None:
        filters.append(address_filter)

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

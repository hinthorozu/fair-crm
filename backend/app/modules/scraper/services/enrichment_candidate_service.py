"""Find CRM customers eligible for website contact enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel


@dataclass(frozen=True)
class EnrichmentCandidate:
    customer_id: UUID
    company_name: str
    website: str


def list_enrichment_candidates(
    session: Session,
    organization_id: UUID,
    *,
    limit: int | None = None,
) -> list[EnrichmentCandidate]:
    """Return active customers with a website and no email records."""
    customers_with_email = {
        row[0]
        for row in session.query(CustomerEmailModel.customer_id)
        .filter(CustomerEmailModel.organization_id == organization_id)
        .distinct()
        .all()
    }

    rows = (
        session.query(CustomerWebsiteModel, CustomerModel)
        .join(CustomerModel, CustomerModel.id == CustomerWebsiteModel.customer_id)
        .filter(
            CustomerModel.organization_id == organization_id,
            CustomerModel.deleted_at.is_(None),
            CustomerWebsiteModel.organization_id == organization_id,
        )
        .order_by(
            CustomerWebsiteModel.is_primary.desc(),
            CustomerWebsiteModel.created_at.asc(),
            CustomerModel.display_name.asc(),
        )
        .all()
    )

    seen_customer_ids: set[UUID] = set()
    candidates: list[EnrichmentCandidate] = []

    for website_model, customer in rows:
        if customer.id in customers_with_email:
            continue
        if customer.id in seen_customer_ids:
            continue

        website = (website_model.website or "").strip()
        if not website:
            continue

        seen_customer_ids.add(customer.id)
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

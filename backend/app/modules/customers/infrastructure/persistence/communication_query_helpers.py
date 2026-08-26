"""SQL helpers for querying customer communication child tables."""

from __future__ import annotations

from sqlalchemy import exists, func, select

from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerPhoneModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.participations.infrastructure.persistence.models import (
    CustomerFairParticipationModel,
)


def primary_phone_subquery():
    return (
        select(CustomerPhoneModel.phone)
        .where(CustomerPhoneModel.customer_id == CustomerModel.id)
        .order_by(CustomerPhoneModel.is_primary.desc(), CustomerPhoneModel.created_at.asc())
        .limit(1)
        .correlate(CustomerModel)
        .scalar_subquery()
    )


def primary_email_subquery():
    return (
        select(CustomerEmailModel.email)
        .where(CustomerEmailModel.customer_id == CustomerModel.id)
        .order_by(CustomerEmailModel.is_primary.desc(), CustomerEmailModel.created_at.asc())
        .limit(1)
        .correlate(CustomerModel)
        .scalar_subquery()
    )


def primary_website_subquery():
    return (
        select(CustomerWebsiteModel.website)
        .where(CustomerWebsiteModel.customer_id == CustomerModel.id)
        .order_by(CustomerWebsiteModel.is_primary.desc(), CustomerWebsiteModel.created_at.asc())
        .limit(1)
        .correlate(CustomerModel)
        .scalar_subquery()
    )


def phone_search_exists(pattern: str):
    return exists(
        select(1).where(
            CustomerPhoneModel.customer_id == CustomerModel.id,
            CustomerPhoneModel.phone.ilike(pattern),
        )
    )


def email_search_exists(pattern: str):
    return exists(
        select(1).where(
            CustomerEmailModel.customer_id == CustomerModel.id,
            CustomerEmailModel.email.ilike(pattern),
        )
    )


def website_search_exists(pattern: str):
    return exists(
        select(1).where(
            CustomerWebsiteModel.customer_id == CustomerModel.id,
            CustomerWebsiteModel.website.ilike(pattern),
        )
    )


def has_usable_website_exists():
    """True when the customer has at least one non-blank website value."""
    return exists(
        select(1).where(
            CustomerWebsiteModel.customer_id == CustomerModel.id,
            CustomerWebsiteModel.website.isnot(None),
            func.trim(CustomerWebsiteModel.website) != "",
        )
    )


def has_usable_phone_exists():
    """True when the customer has at least one non-blank phone value."""
    return exists(
        select(1).where(
            CustomerPhoneModel.customer_id == CustomerModel.id,
            CustomerPhoneModel.phone.isnot(None),
            func.trim(CustomerPhoneModel.phone) != "",
        )
    )


def has_usable_email_exists():
    """True when the customer has at least one non-blank email value."""
    return exists(
        select(1).where(
            CustomerEmailModel.customer_id == CustomerModel.id,
            CustomerEmailModel.email.isnot(None),
            func.trim(CustomerEmailModel.email) != "",
        )
    )


def has_live_fair_participation_exists():
    """True when the customer has any non-deleted fair participation."""
    return exists(
        select(1).where(
            CustomerFairParticipationModel.customer_id == CustomerModel.id,
            CustomerFairParticipationModel.organization_id == CustomerModel.organization_id,
            CustomerFairParticipationModel.deleted_at.is_(None),
        )
    )

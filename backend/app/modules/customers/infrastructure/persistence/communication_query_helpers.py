"""SQL helpers for querying customer communication child tables."""

from __future__ import annotations

from sqlalchemy import exists, select

from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerPhoneModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel


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

"""Filters for which customers participate in duplicate analysis and merge workflows."""

from __future__ import annotations

from sqlalchemy.orm import Query

from app.modules.customers.domain.value_objects import CustomerStatus
from app.modules.customers.infrastructure.persistence.models import CustomerModel


def exclude_merge_deleted_customers(query: Query) -> Query:
    """Include active and archived customers; exclude merge-deleted customers."""
    return query.filter(CustomerModel.status != CustomerStatus.DELETED.value)


def is_merge_deleted_status(status: str) -> bool:
    return status == CustomerStatus.DELETED.value

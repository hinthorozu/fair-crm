"""Tests for customer list query performance characteristics."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.customers.infrastructure.repositories.customer_repository import SqlAlchemyCustomerRepository


def _seed(db_session, organization_id, index: int) -> None:
    now = datetime.now(tz=UTC)
    db_session.add(
        CustomerModel(
            id=uuid4(),
            organization_id=organization_id,
            display_name=f"Perf Customer {index:04d}",
            normalized_name=f"perf customer {index:04d}",
            customer_type=CustomerType.LEAD.value,
            status=CustomerStatus.ACTIVE.value,
            source="manual",
            created_at=now,
            updated_at=now,
        )
    )


def test_list_by_organization_returns_paginated_results(db_session, organization_id):
    for index in range(40):
        _seed(db_session, organization_id, index)
    db_session.flush()

    repo = SqlAlchemyCustomerRepository(db_session)
    result = repo.list_by_organization(
        organization_id,
        page=1,
        page_size=25,
        sort_by="display_name",
        sort_dir="asc",
    )

    assert result.total == 40
    assert len(result.items) == 25


def test_analyze_customer_groups_by_field_not_used_by_list_repository(db_session, organization_id, monkeypatch):
    called = False

    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("duplicate analysis invoked from list path")

    monkeypatch.setattr(
        "app.modules.customers.application.customer_field_grouping.analyze_customer_groups_by_field",
        forbidden,
    )

    _seed(db_session, organization_id, 1)
    db_session.flush()
    repo = SqlAlchemyCustomerRepository(db_session)
    repo.list_by_organization(organization_id, page=1, page_size=25)

    assert called is False

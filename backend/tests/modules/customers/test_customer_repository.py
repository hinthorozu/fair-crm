from datetime import UTC, datetime
from uuid import uuid4

from app.modules.customers.domain.entities import Customer
from app.modules.customers.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)


def _seed_customer(session, organization_id, display_name: str) -> Customer:
    now = datetime.now(tz=UTC)
    customer = Customer.create(
        organization_id=organization_id,
        display_name=display_name,
        city="Istanbul",
        district="Kadikoy",
        address="Test Street 1",
        now=now,
    )
    repo = SqlAlchemyCustomerRepository(session)
    return repo.add(customer)


def test_org_isolation(db_session, organization_id, other_organization_id):
    repo = SqlAlchemyCustomerRepository(db_session)
    saved = _seed_customer(db_session, organization_id, "Org A Customer")

    assert repo.get_by_id(organization_id, saved.id) is not None
    assert repo.get_by_id(other_organization_id, saved.id) is None


def test_search_includes_address(db_session, organization_id):
    repo = SqlAlchemyCustomerRepository(db_session)
    _seed_customer(db_session, organization_id, "Hidden Name Corp")

    result = repo.list_by_organization(organization_id, search="Test Street")
    assert len(result.items) == 1
    assert result.items[0].address == "Test Street 1"


def test_find_by_normalized_name(db_session, organization_id):
    repo = SqlAlchemyCustomerRepository(db_session)
    saved = _seed_customer(db_session, organization_id, "Mega Kalip A.Ş.")

    matches = repo.find_by_normalized_name(organization_id, saved.normalized_name)
    assert len(matches) == 1
    assert matches[0].id == saved.id


def test_list_page_pagination(db_session, organization_id):
    repo = SqlAlchemyCustomerRepository(db_session)
    for index in range(3):
        _seed_customer(db_session, organization_id, f"Customer {index}")

    first_page = repo.list_by_organization(organization_id, page=1, page_size=2)
    assert len(first_page.items) == 2
    assert first_page.page == 1
    assert first_page.page_size == 2
    assert first_page.total == 3
    assert first_page.total_pages == 2

    second_page = repo.list_by_organization(organization_id, page=2, page_size=2)
    assert len(second_page.items) == 1
    assert second_page.page == 2


def test_list_archived_customers(db_session, organization_id):
    from datetime import UTC, datetime

    from app.modules.customers.domain.value_objects import CustomerStatus

    repo = SqlAlchemyCustomerRepository(db_session)
    active = _seed_customer(db_session, organization_id, "Active Customer")
    archived = _seed_customer(db_session, organization_id, "Archived Customer")
    archived.archive(now=datetime.now(tz=UTC))
    repo.update(archived)

    default_list = repo.list_by_organization(organization_id)
    assert len(default_list.items) == 2
    default_ids = {item.id for item in default_list.items}
    assert active.id in default_ids
    assert archived.id in default_ids

    archived_list = repo.list_by_organization(
        organization_id, status=CustomerStatus.ARCHIVED
    )
    assert len(archived_list.items) == 1
    assert archived_list.items[0].id == archived.id
    assert archived_list.items[0].status == CustomerStatus.ARCHIVED

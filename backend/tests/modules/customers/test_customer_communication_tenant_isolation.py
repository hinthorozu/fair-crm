"""P0.1 tenant-isolation tests for customer communication child records."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerPhoneModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.communication_query_helpers import (
    email_search_exists,
    has_usable_email_exists,
    has_usable_phone_exists,
    has_usable_website_exists,
    phone_search_exists,
    primary_email_subquery,
    primary_phone_subquery,
    primary_website_subquery,
    website_search_exists,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)


def _customer(organization_id, *, name: str) -> CustomerModel:
    now = datetime.now(tz=UTC)
    return CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name=name,
        legal_name=None,
        trade_name=None,
        normalized_name=name.lower(),
        customer_type="other",
        status="active",
        tax_number=None,
        tax_office=None,
        country=None,
        city=None,
        district=None,
        address=None,
        description=None,
        instagram_url=None,
        facebook_url=None,
        linkedin_url=None,
        youtube_url=None,
        source="manual",
        email_allowed=True,
        sms_allowed=True,
        email_unsubscribed_at=None,
        sms_unsubscribed_at=None,
        consent_note=None,
        created_at=now,
        updated_at=now,
        deleted_at=None,
        archived_from_status=None,
    )


def test_foreign_parent_cannot_be_used_to_read_cross_linked_child(db_session):
    owner_org = uuid4()
    foreign_org = uuid4()
    foreign_customer = _customer(foreign_org, name="Foreign Customer")
    db_session.add(foreign_customer)
    db_session.flush()

    # Corrupt/cross-linked fixture: child claims Org A but parent belongs to Org B.
    db_session.add(
        CustomerEmailModel(
            id=uuid4(),
            organization_id=owner_org,
            customer_id=foreign_customer.id,
            email="must-not-leak@example.com",
            is_primary=True,
            created_at=datetime.now(tz=UTC),
        )
    )
    db_session.commit()

    repository = SqlAlchemyCustomerCommunicationRepository(db_session)
    with pytest.raises(LookupError):
        repository.load_for_customer(owner_org, foreign_customer.id)

    assert repository.load_list_summaries(owner_org, [foreign_customer.id]) == {}
    assert repository.load_for_customers(owner_org, [foreign_customer.id]) == {}


def test_foreign_parent_cannot_be_used_for_replace(db_session):
    owner_org = uuid4()
    foreign_org = uuid4()
    foreign_customer = _customer(foreign_org, name="Foreign Customer")
    db_session.add(foreign_customer)
    db_session.flush()
    original = CustomerEmailModel(
        id=uuid4(),
        organization_id=foreign_org,
        customer_id=foreign_customer.id,
        email="foreign-owner@example.com",
        is_primary=True,
        created_at=datetime.now(tz=UTC),
    )
    db_session.add(original)
    db_session.commit()

    repository = SqlAlchemyCustomerCommunicationRepository(db_session)
    with pytest.raises(LookupError):
        repository.replace_emails(
            organization_id=owner_org,
            customer_id=foreign_customer.id,
            emails=["attacker@example.com"],
            now=datetime.now(tz=UTC),
        )

    db_session.expire_all()
    stored = db_session.query(CustomerEmailModel).filter(CustomerEmailModel.id == original.id).one()
    assert stored.organization_id == foreign_org
    assert stored.email == "foreign-owner@example.com"


def test_replace_does_not_delete_cross_organization_child_rows(db_session):
    owner_org = uuid4()
    foreign_org = uuid4()
    customer = _customer(owner_org, name="Owner Customer")
    db_session.add(customer)
    db_session.flush()
    now = datetime.now(tz=UTC)

    owner_phone = CustomerPhoneModel(
        id=uuid4(),
        organization_id=owner_org,
        customer_id=customer.id,
        phone="111111",
        is_primary=True,
        created_at=now,
    )
    corrupt_foreign_phone = CustomerPhoneModel(
        id=uuid4(),
        organization_id=foreign_org,
        customer_id=customer.id,
        phone="222222",
        is_primary=True,
        created_at=now,
    )
    db_session.add_all([owner_phone, corrupt_foreign_phone])
    db_session.commit()

    repository = SqlAlchemyCustomerCommunicationRepository(db_session)
    repository.replace_phones(
        organization_id=owner_org,
        customer_id=customer.id,
        phones=["333333"],
        now=datetime.now(tz=UTC),
    )
    db_session.commit()

    owner_rows = (
        db_session.query(CustomerPhoneModel)
        .filter(
            CustomerPhoneModel.organization_id == owner_org,
            CustomerPhoneModel.customer_id == customer.id,
        )
        .all()
    )
    foreign_rows = (
        db_session.query(CustomerPhoneModel)
        .filter(
            CustomerPhoneModel.organization_id == foreign_org,
            CustomerPhoneModel.customer_id == customer.id,
        )
        .all()
    )
    assert [row.phone for row in owner_rows] == ["333333"]
    assert [row.phone for row in foreign_rows] == ["222222"]


def test_query_helpers_ignore_cross_organization_child_rows(db_session):
    owner_org = uuid4()
    foreign_org = uuid4()
    customer = _customer(owner_org, name="Helper Owner Customer")
    db_session.add(customer)
    db_session.flush()
    now = datetime.now(tz=UTC)

    db_session.add_all(
        [
            CustomerPhoneModel(
                id=uuid4(),
                organization_id=foreign_org,
                customer_id=customer.id,
                phone="999999",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=foreign_org,
                customer_id=customer.id,
                email="foreign-helper@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerWebsiteModel(
                id=uuid4(),
                organization_id=foreign_org,
                customer_id=customer.id,
                website="https://foreign-helper.example",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.commit()

    row = db_session.execute(
        select(
            primary_phone_subquery().label("phone"),
            primary_email_subquery().label("email"),
            primary_website_subquery().label("website"),
            phone_search_exists("%999999%").label("phone_match"),
            email_search_exists("%foreign-helper%").label("email_match"),
            website_search_exists("%foreign-helper%").label("website_match"),
            has_usable_phone_exists().label("has_phone"),
            has_usable_email_exists().label("has_email"),
            has_usable_website_exists().label("has_website"),
        )
        .select_from(CustomerModel)
        .where(
            CustomerModel.id == customer.id,
            CustomerModel.organization_id == owner_org,
        )
    ).one()

    assert row.phone is None
    assert row.email is None
    assert row.website is None
    assert not row.phone_match
    assert not row.email_match
    assert not row.website_match
    assert not row.has_phone
    assert not row.has_email
    assert not row.has_website

from datetime import UTC, datetime

import pytest

from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.exceptions import (
    CustomerAlreadyArchivedError,
    InvalidCustomerEmailError,
    InvalidCustomerNameError,
)
from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType


def test_create_customer_computes_normalized_name():
    now = datetime.now(tz=UTC)
    customer = Customer.create(
        organization_id=__import__("uuid").uuid4(),
        display_name="Acme A.Ş.",
        now=now,
    )
    assert customer.normalized_name == "ACME"
    assert customer.customer_type == CustomerType.LEAD
    assert customer.status == CustomerStatus.LEAD


def test_empty_display_name_raises():
    with pytest.raises(InvalidCustomerNameError):
        Customer.create(
            organization_id=__import__("uuid").uuid4(),
            display_name="   ",
            now=datetime.now(tz=UTC),
        )


def test_invalid_email_raises():
    with pytest.raises(InvalidCustomerEmailError, match="Invalid email address: not-an-email"):
        Customer.create(
            organization_id=__import__("uuid").uuid4(),
            display_name="Acme",
            email="not-an-email",
            now=datetime.now(tz=UTC),
        )


def test_multi_email_normalized_on_create():
    now = datetime.now(tz=UTC)
    customer = Customer.create(
        organization_id=__import__("uuid").uuid4(),
        display_name="Acme",
        email="info@abc.com ; sales@abc.com, info@abc.com",
        now=now,
    )
    assert customer.email == "info@abc.com;sales@abc.com"


def test_archive_customer():
    now = datetime.now(tz=UTC)
    customer = Customer.create(
        organization_id=__import__("uuid").uuid4(),
        display_name="Acme",
        now=now,
    )
    customer.archive(now=now)
    assert customer.status == CustomerStatus.ARCHIVED
    assert customer.deleted_at is not None


def test_cannot_update_archived_customer():
    now = datetime.now(tz=UTC)
    customer = Customer.create(
        organization_id=__import__("uuid").uuid4(),
        display_name="Acme",
        now=now,
    )
    customer.archive(now=now)
    with pytest.raises(CustomerAlreadyArchivedError):
        customer.update_fields(display_name="New", now=now)

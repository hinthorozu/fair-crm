from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.contacts.domain.entities import Contact
from app.modules.contacts.domain.exceptions import InvalidContactEmailError, InvalidContactNameError


def test_contact_full_name_computed():
    contact = Contact.create(
        organization_id=uuid4(),
        customer_id=uuid4(),
        first_name="Ali",
        last_name="Yılmaz",
        now=datetime.now(tz=UTC),
    )
    assert contact.full_name == "Ali Yılmaz"


def test_contact_requires_first_and_last_name():
    with pytest.raises(InvalidContactNameError):
        Contact.create(
            organization_id=uuid4(),
            customer_id=uuid4(),
            first_name="",
            last_name="Test",
            now=datetime.now(tz=UTC),
        )


def test_contact_invalid_email():
    with pytest.raises(InvalidContactEmailError):
        Contact.create(
            organization_id=uuid4(),
            customer_id=uuid4(),
            first_name="Ali",
            last_name="Test",
            email="not-an-email",
            now=datetime.now(tz=UTC),
        )


def test_contact_soft_delete_clears_primary():
    contact = Contact.create(
        organization_id=uuid4(),
        customer_id=uuid4(),
        first_name="Ali",
        last_name="Test",
        is_primary=True,
        now=datetime.now(tz=UTC),
    )
    now = datetime.now(tz=UTC)
    contact.soft_delete(now=now)
    assert contact.deleted_at is not None
    assert contact.is_primary is False
    assert contact.is_active is False

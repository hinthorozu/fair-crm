"""Contact import field resolution and duplicate matching tests."""

from uuid import uuid4

import pytest

from app.modules.contacts.domain.entities import Contact
from app.modules.imports.domain.services.contact_import import (
    find_existing_contact_for_import,
    has_contact_import_fields,
    resolve_contact_identity,
)


def test_has_contact_import_fields_requires_nonempty_value():
    assert has_contact_import_fields({}) is False
    assert has_contact_import_fields({"contact_first_name": "  "}) is False
    assert has_contact_import_fields({"contact_email": "a@b.com"}) is True
    assert has_contact_import_fields({"contact_phone": "5551234567"}) is True


def test_resolve_contact_identity_splits_yetkili_adi():
    assert resolve_contact_identity({"contact_first_name": "Ali Veli"}) == ("Ali", "Veli")


def test_resolve_contact_identity_uses_placeholder_for_single_name():
    first, last = resolve_contact_identity({"contact_first_name": "Ali"})
    assert first == "Ali"
    assert last == "—"


def test_resolve_contact_identity_from_email_when_name_missing():
    first, last = resolve_contact_identity({"contact_email": "mehmet.demir@example.com"})
    assert first == "Mehmet"
    assert last == "Demir"


def test_resolve_contact_identity_defaults_when_only_phone():
    first, last = resolve_contact_identity({"contact_phone": "5551234567"})
    assert first == "Yetkili"
    assert last == "—"


class _FakeContactRepository:
    def __init__(self, contacts: list[Contact]) -> None:
        self._contacts = contacts

    def find_by_customer_and_email(self, organization_id, customer_id, email_normalized):
        for contact in self._contacts:
            if contact.email and contact.email.lower() == email_normalized.lower():
                return contact
        return None

    def find_by_customer_and_phone(self, organization_id, customer_id, phone_normalized):
        from app.modules.contacts.domain.services.normalizers import normalize_phone

        target = phone_normalized.strip()
        for contact in self._contacts:
            for raw in (contact.phone, contact.mobile_phone):
                if not raw:
                    continue
                try:
                    normalized = normalize_phone(raw)
                except ValueError:
                    normalized = raw.strip()
                if normalized == target:
                    return contact
        return None

    def find_by_customer_and_name(self, organization_id, customer_id, first_name_lower, last_name_lower):
        for contact in self._contacts:
            if (
                contact.first_name.strip().lower() == first_name_lower
                and contact.last_name.strip().lower() == last_name_lower
            ):
                return contact
        return None


@pytest.fixture
def org_and_customer():
    return uuid4(), uuid4()


def test_find_existing_contact_prefers_email_over_name(org_and_customer):
    organization_id, customer_id = org_and_customer
    from datetime import UTC, datetime

    now = datetime.now(tz=UTC)
    existing = Contact(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=customer_id,
        first_name="Old",
        last_name="Name",
        title=None,
        department=None,
        email="person@example.com",
        phone=None,
        mobile_phone=None,
        linkedin=None,
        notes=None,
        is_primary=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    repo = _FakeContactRepository([existing])
    found = find_existing_contact_for_import(
        repo,
        organization_id=organization_id,
        customer_id=customer_id,
        data={
            "contact_first_name": "New",
            "contact_last_name": "Person",
            "contact_email": "person@example.com",
        },
    )
    assert found is existing


def test_find_existing_contact_matches_phone_when_email_missing(org_and_customer):
    organization_id, customer_id = org_and_customer
    from datetime import UTC, datetime

    now = datetime.now(tz=UTC)
    existing = Contact(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=customer_id,
        first_name="Phone",
        last_name="Owner",
        title=None,
        department=None,
        email=None,
        phone="+905551234567",
        mobile_phone=None,
        linkedin=None,
        notes=None,
        is_primary=False,
        is_active=True,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    repo = _FakeContactRepository([existing])
    found = find_existing_contact_for_import(
        repo,
        organization_id=organization_id,
        customer_id=customer_id,
        data={"contact_phone": "5551234567", "contact_first_name": "Other"},
    )
    assert found is existing

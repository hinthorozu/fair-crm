from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.modules.contacts.domain.entities import Contact


@dataclass(frozen=True)
class ContactListResult:
    items: list[Contact]
    page: int
    page_size: int
    total: int
    total_pages: int


class ContactRepository(Protocol):
    def add(self, contact: Contact) -> Contact: ...

    def get_by_id(self, organization_id: UUID, contact_id: UUID) -> Contact | None: ...

    def update(self, contact: Contact) -> Contact: ...

    def list_by_customer(
        self,
        organization_id: UUID,
        customer_id: UUID,
        *,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "first_name",
        sort_dir: str = "asc",
        include_deleted: bool = False,
    ) -> ContactListResult: ...

    def find_by_customer_and_name(
        self,
        organization_id: UUID,
        customer_id: UUID,
        first_name_lower: str,
        last_name_lower: str,
    ) -> Contact | None: ...

    def find_by_customer_and_email(
        self,
        organization_id: UUID,
        customer_id: UUID,
        email_normalized: str,
    ) -> Contact | None: ...

    def find_by_customer_and_phone(
        self,
        organization_id: UUID,
        customer_id: UUID,
        phone_normalized: str,
    ) -> Contact | None: ...

    def clear_primary_for_customer(
        self,
        organization_id: UUID,
        customer_id: UUID,
        *,
        exclude_contact_id: UUID | None = None,
    ) -> None: ...

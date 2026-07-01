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
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        include_deleted: bool = False,
    ) -> ContactListResult: ...

    def clear_primary_for_customer(
        self,
        organization_id: UUID,
        customer_id: UUID,
        *,
        exclude_contact_id: UUID | None = None,
    ) -> None: ...

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType


@dataclass
class CustomerListResult:
    items: list[Customer]
    page: int
    page_size: int
    total: int
    total_pages: int


class CustomerRepository(Protocol):
    def add(self, customer: Customer) -> Customer: ...

    def get_by_id(self, organization_id: UUID, customer_id: UUID) -> Customer | None: ...

    def get_by_id_including_archived(
        self, organization_id: UUID, customer_id: UUID
    ) -> Customer | None: ...

    def update(self, customer: Customer) -> Customer: ...

    def list_by_organization(
        self,
        organization_id: UUID,
        *,
        status: CustomerStatus | None = None,
        include_archived: bool = False,
        customer_type: CustomerType | None = None,
        country: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "display_name",
        sort_dir: str = "asc",
    ) -> CustomerListResult: ...

    def list_all_active(self, organization_id: UUID) -> list[Customer]: ...

    def find_by_normalized_name(
        self,
        organization_id: UUID,
        normalized_name: str,
        *,
        exclude_id: UUID | None = None,
    ) -> list[Customer]: ...

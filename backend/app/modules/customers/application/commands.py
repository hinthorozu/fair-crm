from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.modules.customers.domain.value_objects import CustomerSource, CustomerStatus, CustomerType


@dataclass(frozen=True)
class CreateCustomerCommand:
    organization_id: UUID
    access_token: str
    user_id: UUID
    display_name: str
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    customer_type: CustomerType = CustomerType.LEAD
    status: CustomerStatus = CustomerStatus.LEAD
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    tax_number: Optional[str] = None
    tax_office: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    source: CustomerSource = CustomerSource.MANUAL


@dataclass(frozen=True)
class GetCustomerQuery:
    organization_id: UUID
    customer_id: UUID


@dataclass(frozen=True)
class ListCustomersQuery:
    organization_id: UUID
    status: CustomerStatus | None = None
    include_archived: bool = False
    customer_type: CustomerType | None = None
    country: str | None = None
    search: str | None = None
    page: int = 1
    page_size: int = 25
    sort_by: str = "name"
    sort_dir: str = "asc"


@dataclass(frozen=True)
class UpdateCustomerCommand:
    organization_id: UUID
    customer_id: UUID
    access_token: str
    user_id: UUID
    display_name: Optional[str] = None
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    customer_type: Optional[CustomerType] = None
    status: Optional[CustomerStatus] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    tax_number: Optional[str] = None
    tax_office: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    source: Optional[CustomerSource] = None


@dataclass(frozen=True)
class ArchiveCustomerCommand:
    organization_id: UUID
    customer_id: UUID
    access_token: str
    user_id: UUID


@dataclass(frozen=True)
class RestoreCustomerCommand:
    organization_id: UUID
    customer_id: UUID
    access_token: str
    user_id: UUID


@dataclass(frozen=True)
class CustomerResult:
    id: UUID
    organization_id: UUID
    display_name: str
    legal_name: Optional[str]
    trade_name: Optional[str]
    normalized_name: str
    customer_type: CustomerType
    status: CustomerStatus
    website: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    tax_number: Optional[str]
    tax_office: Optional[str]
    country: Optional[str]
    city: Optional[str]
    district: Optional[str]
    address: Optional[str]
    description: Optional[str]
    source: CustomerSource
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
    possible_duplicates: list[UUID] | None = None


@dataclass(frozen=True)
class CustomerListResultDto:
    items: list[CustomerResult]
    page: int
    page_size: int
    total: int
    total_pages: int

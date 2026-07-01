from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class CreateContactCommand:
    organization_id: UUID
    access_token: str
    user_id: UUID
    customer_id: UUID
    first_name: str
    last_name: str
    title: Optional[str] = None
    department: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    linkedin: Optional[str] = None
    notes: Optional[str] = None
    is_primary: bool = False
    is_active: bool = True


@dataclass(frozen=True)
class GetContactQuery:
    organization_id: UUID
    contact_id: UUID


@dataclass(frozen=True)
class ListContactsByCustomerQuery:
    organization_id: UUID
    customer_id: UUID
    search: str | None = None
    page: int = 1
    page_size: int = 25
    sort_by: str = "first_name"
    sort_dir: str = "asc"


@dataclass(frozen=True)
class UpdateContactCommand:
    organization_id: UUID
    contact_id: UUID
    access_token: str
    user_id: UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    linkedin: Optional[str] = None
    notes: Optional[str] = None
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None


@dataclass(frozen=True)
class DeleteContactCommand:
    organization_id: UUID
    contact_id: UUID
    access_token: str
    user_id: UUID


@dataclass(frozen=True)
class ContactResult:
    id: UUID
    organization_id: UUID
    customer_id: UUID
    first_name: str
    last_name: str
    full_name: str
    title: Optional[str]
    department: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    mobile_phone: Optional[str]
    linkedin: Optional[str]
    notes: Optional[str]
    is_primary: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]


@dataclass(frozen=True)
class ContactListResultDto:
    items: list[ContactResult]
    page: int
    page_size: int
    total: int
    total_pages: int

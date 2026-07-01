from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class CreateActivityCommand:
    organization_id: UUID
    access_token: str
    user_id: UUID
    customer_id: UUID
    activity_type: str
    subject: str
    activity_date: datetime
    status: str
    contact_id: Optional[UUID] = None
    description: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    source: str = "manual"
    is_active: bool = True


@dataclass(frozen=True)
class GetActivityQuery:
    organization_id: UUID
    activity_id: UUID


@dataclass(frozen=True)
class ListActivitiesByCustomerQuery:
    organization_id: UUID
    customer_id: UUID
    search: str | None = None
    activity_type: str | None = None
    page: int = 1
    page_size: int = 25
    sort_by: str = "activity_date"
    sort_dir: str = "desc"


@dataclass(frozen=True)
class UpdateActivityCommand:
    organization_id: UUID
    activity_id: UUID
    access_token: str
    user_id: UUID
    contact_id: Optional[UUID] = None
    activity_type: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    activity_date: Optional[datetime] = None
    follow_up_date: Optional[datetime] = None
    status: Optional[str] = None
    source: Optional[str] = None
    is_active: Optional[bool] = None
    set_contact_id: bool = False
    set_description: bool = False
    set_follow_up_date: bool = False


@dataclass(frozen=True)
class DeleteActivityCommand:
    organization_id: UUID
    activity_id: UUID
    access_token: str
    user_id: UUID


@dataclass(frozen=True)
class ActivityResult:
    id: UUID
    organization_id: UUID
    customer_id: UUID
    contact_id: Optional[UUID]
    contact_full_name: Optional[str]
    type: str
    subject: str
    description: Optional[str]
    activity_date: datetime
    follow_up_date: Optional[datetime]
    status: str
    source: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]


@dataclass(frozen=True)
class ActivityListResultDto:
    items: list[ActivityResult]
    page: int
    page_size: int
    total: int
    total_pages: int

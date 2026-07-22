from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class CreateParticipationCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    customer_id: UUID
    fair_id: UUID
    hall: Optional[str] = None
    stand: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class UpdateParticipationCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    participation_id: UUID
    hall: Optional[str] = None
    stand: Optional[str] = None
    notes: Optional[str] = None
    set_hall: bool = False
    set_stand: bool = False
    set_notes: bool = False


@dataclass(frozen=True)
class DeleteParticipationCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    participation_id: UUID


@dataclass(frozen=True)
class GetParticipationQuery:
    organization_id: UUID
    participation_id: UUID


@dataclass(frozen=True)
class ListParticipationsByCustomerQuery:
    organization_id: UUID
    customer_id: UUID
    search: str | None = None
    page: int = 1
    page_size: int = 25
    sort_by: str = "fair_start_date"
    sort_dir: str = "desc"


@dataclass(frozen=True)
class ListParticipantsByFairQuery:
    organization_id: UUID
    fair_id: UUID
    search: str | None = None
    page: int = 1
    page_size: int = 25
    sort_by: str = "company_name"
    sort_dir: str = "asc"


@dataclass
class ParticipationResult:
    id: UUID
    organization_id: UUID
    customer_id: UUID
    fair_id: UUID
    hall: Optional[str]
    stand: Optional[str]
    notes: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]


@dataclass
class CustomerParticipationListItem:
    id: UUID
    fair_id: UUID
    fair_name: str
    fair_start_date: Optional[date]
    fair_end_date: Optional[date]
    hall: Optional[str]
    stand: Optional[str]
    notes: Optional[str]


@dataclass
class CustomerParticipationListResultDto:
    items: list[CustomerParticipationListItem]
    page: int
    page_size: int
    total: int
    total_pages: int


@dataclass
class FairParticipantListItem:
    id: UUID
    customer_id: UUID
    company_name: str
    email: Optional[str]
    phone: Optional[str]
    country: Optional[str]
    city: Optional[str]
    hall: Optional[str]
    stand: Optional[str]
    notes: Optional[str]


@dataclass
class FairParticipantListResultDto:
    items: list[FairParticipantListItem]
    page: int
    page_size: int
    total: int
    total_pages: int

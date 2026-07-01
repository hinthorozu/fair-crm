from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from app.modules.fairs.domain.value_objects import FairStatus


@dataclass(frozen=True)
class CreateFairCommand:
    organization_id: UUID
    access_token: str
    user_id: UUID
    name: str
    organizer: Optional[str] = None
    venue: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    website: Optional[str] = None
    status: FairStatus = FairStatus.PLANNED
    description: Optional[str] = None


@dataclass(frozen=True)
class GetFairQuery:
    organization_id: UUID
    fair_id: UUID


@dataclass(frozen=True)
class ListFairsQuery:
    organization_id: UUID
    status: FairStatus | None = None
    include_archived: bool = False
    country: str | None = None
    search: str | None = None
    page: int = 1
    page_size: int = 25
    sort_by: str = "start_date"
    sort_dir: str = "desc"


@dataclass(frozen=True)
class UpdateFairCommand:
    organization_id: UUID
    fair_id: UUID
    access_token: str
    user_id: UUID
    name: Optional[str] = None
    organizer: Optional[str] = None
    venue: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    website: Optional[str] = None
    status: Optional[FairStatus] = None
    description: Optional[str] = None


@dataclass(frozen=True)
class ArchiveFairCommand:
    organization_id: UUID
    fair_id: UUID
    access_token: str
    user_id: UUID


@dataclass(frozen=True)
class RestoreFairCommand:
    organization_id: UUID
    fair_id: UUID
    access_token: str
    user_id: UUID


@dataclass(frozen=True)
class FairResult:
    id: UUID
    organization_id: UUID
    name: str
    organizer: Optional[str]
    venue: Optional[str]
    city: Optional[str]
    country: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    website: Optional[str]
    status: FairStatus
    description: Optional[str]
    normalized_name: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]


@dataclass(frozen=True)
class FairListResultDto:
    items: list[FairResult]
    page: int
    page_size: int
    total: int
    total_pages: int

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.list_response import StandardListResponse

from app.modules.fairs.domain.value_objects import FairStatus


class CreateFairRequest(BaseModel):
    name: str = Field(..., min_length=1)
    organizer: Optional[str] = Field(default=None, max_length=255)
    venue: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    website: Optional[str] = Field(default=None, max_length=255)
    status: FairStatus = FairStatus.PLANNED
    description: Optional[str] = Field(default=None, max_length=5000)
    adapter_key: Optional[str] = Field(default=None, max_length=100)
    source_url: Optional[str] = Field(default=None, max_length=5000)
    scraper_config: Optional[dict[str, Any]] = None


class UpdateFairRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    organizer: Optional[str] = Field(default=None, max_length=255)
    venue: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    website: Optional[str] = Field(default=None, max_length=255)
    status: Optional[FairStatus] = None
    description: Optional[str] = Field(default=None, max_length=5000)
    adapter_key: Optional[str] = Field(default=None, max_length=100)
    source_url: Optional[str] = Field(default=None, max_length=5000)
    scraper_config: Optional[dict[str, Any]] = None


class FairResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID | None
    origin: str
    name: str
    display_name: str
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
    adapter_key: Optional[str] = None
    source_url: Optional[str] = None
    scraper_config: Optional[dict[str, Any]] = None
    scraped_record_count: Optional[int] = None
    scraped_at: Optional[datetime] = None


class FairListResponse(StandardListResponse[FairResponse]):
    pass


class ErrorResponse(BaseModel):
    detail: str


class CompareSystemFairImportResponse(BaseModel):
    batch_id: UUID


class SyncTobbSystemFairsRequest(BaseModel):
    year: int


class TobbSyncConflictItem(BaseModel):
    name: str
    identity_name: str
    city: str | None = None
    fair_ids: list[UUID]


class SyncTobbSystemFairsResponse(BaseModel):
    inserted: int
    updated: int
    conflicts: int
    conflict_items: list[TobbSyncConflictItem] = []


class SystemFairDuplicateFairResponse(BaseModel):
    id: UUID
    name: str
    city: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    organizer: str | None = None
    website: str | None = None
    external_id: str | None = None
    source: str | None = None
    participations: int
    todos: int
    quotes: int
    imports: int
    scraper_runs: int
    has_scraper_config: bool


class SystemFairDuplicateGroupResponse(BaseModel):
    identity_name: str
    city: str | None = None
    fairs: list[SystemFairDuplicateFairResponse]


class SystemFairDuplicateListResponse(BaseModel):
    items: list[SystemFairDuplicateGroupResponse]


class SystemFairMergePreviewRequest(BaseModel):
    source_fair_id: UUID
    target_fair_id: UUID


class SystemFairMergeRequest(BaseModel):
    target_fair_id: UUID


class SystemFairKeepSeparateRequest(BaseModel):
    fair_ids: list[UUID] = Field(min_length=2)


class SystemFairMergeBlockResponse(BaseModel):
    code: str
    message: str


class SystemFairMergePreviewResponse(BaseModel):
    participations: int
    todos: int
    quotes: int
    activities: int
    imports: int
    scraper_runs: int
    email_batches: int
    mail_operations: int
    operations: int
    blocking_conflicts: list[SystemFairMergeBlockResponse]

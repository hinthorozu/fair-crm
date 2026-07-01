from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.list_response import StandardListResponse

from app.modules.fairs.domain.value_objects import FairStatus


class CreateFairRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    organizer: Optional[str] = Field(default=None, max_length=255)
    venue: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    website: Optional[str] = Field(default=None, max_length=255)
    status: FairStatus = FairStatus.PLANNED
    description: Optional[str] = Field(default=None, max_length=5000)


class UpdateFairRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    organizer: Optional[str] = Field(default=None, max_length=255)
    venue: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    website: Optional[str] = Field(default=None, max_length=255)
    status: Optional[FairStatus] = None
    description: Optional[str] = Field(default=None, max_length=5000)


class FairResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class FairListResponse(StandardListResponse[FairResponse]):
    pass


class ErrorResponse(BaseModel):
    detail: str

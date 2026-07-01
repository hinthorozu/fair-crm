from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.pagination import PaginationMeta
from app.modules.activities.domain.value_objects import ActivitySource

ActivityTypeField = Literal[
    "call",
    "meeting",
    "email",
    "whatsapp",
    "note",
    "fair_visit",
    "follow_up",
    "other",
]

ActivityStatusField = Literal["open", "completed", "cancelled"]

ActivitySourceField = Literal[
    "manual",
    "system",
    "email_automation",
    "whatsapp_integration",
    "import",
    "other",
]


class CreateActivityRequest(BaseModel):
    customer_id: UUID
    type: ActivityTypeField = Field(..., description="Activity type")
    subject: str = Field(..., min_length=1, max_length=500)
    activity_date: datetime
    status: ActivityStatusField
    contact_id: Optional[UUID] = None
    description: Optional[str] = Field(default=None, max_length=10000)
    follow_up_date: Optional[datetime] = None
    source: ActivitySourceField = ActivitySource.MANUAL
    is_active: bool = True


class UpdateActivityRequest(BaseModel):
    type: Optional[ActivityTypeField] = Field(default=None, description="Activity type")
    subject: Optional[str] = Field(default=None, min_length=1, max_length=500)
    activity_date: Optional[datetime] = None
    status: Optional[ActivityStatusField] = None
    contact_id: Optional[UUID] = None
    description: Optional[str] = Field(default=None, max_length=10000)
    follow_up_date: Optional[datetime] = None
    source: Optional[ActivitySourceField] = None
    is_active: Optional[bool] = None


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ActivityListResponse(PaginationMeta):
    items: list[ActivityResponse]


class ErrorResponse(BaseModel):
    detail: str

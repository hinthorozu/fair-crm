from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.list_response import StandardListResponse
from app.modules.activities.domain.value_objects import ActivitySource

# Manual create/update types — task_completed is system-only (Todo complete).
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
    customer_id: Optional[UUID]
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
    todo_id: Optional[UUID] = None
    fair_id: Optional[UUID] = None
    customer_name: Optional[str] = None
    related_todo_id: Optional[UUID] = None
    related_todo_title: Optional[str] = None
    related_outcome_id: Optional[UUID] = None
    related_outcome_name: Optional[str] = None
    action_required: Optional[bool] = None
    data_problem: Optional[bool] = None
    display_metadata: Optional[dict] = None


class ActivityListResponse(StandardListResponse[ActivityResponse]):
    pass


class BulkDeleteActivitiesRequest(BaseModel):
    activity_ids: list[UUID] = Field(..., min_length=1, max_length=200)


class BulkDeleteActivitiesResponse(BaseModel):
    deleted_ids: list[UUID]
    not_found_ids: list[UUID]
    deleted_count: int
    not_found_count: int


class ErrorResponse(BaseModel):
    detail: str

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.api.schemas.list_response import StandardListResponse
from app.modules.todos.api.worklist_schemas import WorklistPrimaryStatusField

FollowUpFilterField = Literal["bugun", "gecmis", "action_required", "data_problem", "hepsi"]


class FollowUpRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    todo_id: UUID
    todo_title: str
    customer_id: UUID
    customer_name: str
    city: Optional[str]
    country: Optional[str]
    phone_summary: Optional[str]
    email_summary: Optional[str]
    contact_count: int
    participation_id: Optional[UUID]
    primary_status: WorklistPrimaryStatusField
    last_outcome_id: Optional[UUID]
    last_outcome_name: Optional[str]
    last_note_summary: Optional[str]
    last_activity_at: Optional[datetime]
    follow_up_at: Optional[datetime]
    action_required: bool
    data_problem: bool
    added_after_completion: bool


class FollowUpListResponse(StandardListResponse[FollowUpRowResponse]):
    pass


class ErrorResponse(BaseModel):
    detail: str

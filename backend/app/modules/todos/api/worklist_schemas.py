from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.list_response import StandardListResponse

WorklistFilterField = Literal["yapilmadi", "takipte", "konu_kapandi", "hepsi"]
WorklistPrimaryStatusField = Literal["not_started", "in_follow_up", "closed"]


class TodoWorklistRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: UUID
    customer_name: str
    city: Optional[str]
    country: Optional[str]
    phone_summary: Optional[str]
    email_summary: Optional[str]
    contact_count: int
    participation_id: UUID
    primary_status: WorklistPrimaryStatusField
    last_outcome_id: Optional[UUID]
    last_outcome_name: Optional[str]
    last_note_summary: Optional[str]
    last_activity_at: Optional[datetime]
    follow_up_at: Optional[datetime]
    action_required: bool
    data_problem: bool
    added_after_completion: bool


class TodoWorklistListResponse(StandardListResponse[TodoWorklistRowResponse]):
    pass


class TodoWorklistProgressResponse(BaseModel):
    total: int
    not_started: int
    in_follow_up: int
    closed: int


class ErrorResponse(BaseModel):
    detail: str

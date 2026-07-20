from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.todos.api.outcome_schemas import OutcomePrimaryWorklistStatusField
from app.modules.todos.api.worklist_schemas import (
    TodoWorklistProgressResponse,
    TodoWorklistRowResponse,
)


class RecordTodoWorklistActivityRequest(BaseModel):
    outcome_id: UUID
    note: str = Field(min_length=1)
    activity_type: Literal["call", "meeting", "email", "whatsapp", "note", "fair_visit", "follow_up", "other"] = "call"
    contact_id: Optional[UUID] = None
    follow_up_at: Optional[datetime] = None
    action_required: bool = False
    data_problem: bool = False
    advance_to_next: bool = False


class TodoWorklistActivityResponse(BaseModel):
    activity_id: UUID
    worklist_row: TodoWorklistRowResponse
    progress: TodoWorklistProgressResponse
    next_customer_id: Optional[UUID] = None


class TodoWorklistModalOutcomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    primary_worklist_status: OutcomePrimaryWorklistStatusField
    requires_action: bool
    marks_data_problem: bool


class TodoWorklistModalActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subject: str
    description: Optional[str]
    activity_date: datetime
    follow_up_date: Optional[datetime]


class TodoWorklistModalContextResponse(BaseModel):
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
    worklist_row: Optional[TodoWorklistRowResponse]
    outcomes: list[TodoWorklistModalOutcomeResponse]
    recent_activities: list[TodoWorklistModalActivityResponse]


class SendManualTaskMailRequest(BaseModel):
    smtp_account_id: UUID
    recipients: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)
    template_id: Optional[UUID] = None
    # Echoed for clients that include path ids in the body; path params are authoritative.
    todo_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None


class SendManualTaskMailResponse(BaseModel):
    queued_count: int
    operation_ids: list[UUID]
    message: str

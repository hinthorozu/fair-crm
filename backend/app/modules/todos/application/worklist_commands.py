from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.modules.todos.domain.worklist_value_objects import FollowUpFilter, WorklistFilter


@dataclass(frozen=True)
class TodoWorklistRowResult:
    customer_id: UUID
    customer_name: str
    city: Optional[str]
    country: Optional[str]
    phone_summary: Optional[str]
    email_summary: Optional[str]
    contact_count: int
    participation_id: UUID
    primary_status: str
    last_outcome_id: Optional[UUID]
    last_outcome_name: Optional[str]
    last_note_summary: Optional[str]
    last_activity_at: Optional[datetime]
    follow_up_at: Optional[datetime]
    action_required: bool
    data_problem: bool
    added_after_completion: bool


@dataclass(frozen=True)
class TodoWorklistListResultDto:
    items: list[TodoWorklistRowResult]
    page: int
    page_size: int
    total: int
    total_pages: int


@dataclass(frozen=True)
class TodoWorklistProgressResult:
    total: int
    not_started: int
    in_follow_up: int
    closed: int


@dataclass(frozen=True)
class ListTodoWorklistQuery:
    organization_id: UUID
    todo_id: UUID
    worklist_filter: WorklistFilter = WorklistFilter.YAPILMADI
    search: str | None = None
    page: int = 1
    page_size: int = 25
    sort_by: str = "company_name"
    sort_dir: str = "asc"


@dataclass(frozen=True)
class GetTodoWorklistProgressQuery:
    organization_id: UUID
    todo_id: UUID


@dataclass(frozen=True)
class GetTodoWorklistModalContextQuery:
    organization_id: UUID
    todo_id: UUID
    customer_id: UUID


@dataclass(frozen=True)
class RecordTodoWorklistActivityCommand:
    organization_id: UUID
    access_token: str
    user_id: UUID
    todo_id: UUID
    customer_id: UUID
    outcome_id: UUID
    note: str
    activity_type: str = "call"
    contact_id: UUID | None = None
    follow_up_at: datetime | None = None
    action_required: bool = False
    data_problem: bool = False
    advance_to_next: bool = False


@dataclass(frozen=True)
class TodoWorklistActivityResult:
    activity_id: UUID
    worklist_row: TodoWorklistRowResult
    progress: TodoWorklistProgressResult
    next_customer_id: UUID | None = None


@dataclass(frozen=True)
class TodoWorklistModalOutcomeItem:
    id: UUID
    name: str
    code: str
    primary_worklist_status: str
    requires_action: bool
    marks_data_problem: bool


@dataclass(frozen=True)
class TodoWorklistModalActivityItem:
    id: UUID
    subject: str
    description: str | None
    activity_date: datetime
    follow_up_date: datetime | None


@dataclass(frozen=True)
class TodoWorklistModalContextResult:
    todo_id: UUID
    todo_title: str
    customer_id: UUID
    customer_name: str
    city: str | None
    country: str | None
    phone_summary: str | None
    email_summary: str | None
    contact_count: int
    worklist_row: TodoWorklistRowResult | None
    outcomes: list[TodoWorklistModalOutcomeItem]
    recent_activities: list[TodoWorklistModalActivityItem]


@dataclass(frozen=True)
class FollowUpRowResult:
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
    primary_status: str
    last_outcome_id: Optional[UUID]
    last_outcome_name: Optional[str]
    last_note_summary: Optional[str]
    last_activity_at: Optional[datetime]
    follow_up_at: Optional[datetime]
    action_required: bool
    data_problem: bool
    added_after_completion: bool


@dataclass(frozen=True)
class FollowUpListResultDto:
    items: list[FollowUpRowResult]
    page: int
    page_size: int
    total: int
    total_pages: int


@dataclass(frozen=True)
class ListFollowUpsQuery:
    organization_id: UUID
    follow_up_filter: FollowUpFilter = FollowUpFilter.BUGUN
    search: str | None = None
    page: int = 1
    page_size: int = 25
    sort_by: str = "follow_up_at"
    sort_dir: str = "asc"

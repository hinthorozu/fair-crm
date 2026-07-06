from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.modules.todos.domain.worklist_value_objects import WorklistFilter


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

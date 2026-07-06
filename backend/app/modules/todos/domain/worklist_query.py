from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.modules.todos.domain.worklist_value_objects import WorklistDisplayStatus


@dataclass(frozen=True)
class TodoWorklistRow:
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
class TodoWorklistListResult:
    items: list[TodoWorklistRow]
    page: int
    page_size: int
    total: int
    total_pages: int


@dataclass(frozen=True)
class TodoWorklistProgress:
    total: int
    not_started: int
    in_follow_up: int
    closed: int


def resolve_added_after_completion(
    *,
    participation_created_at: datetime,
    todo_completed_at: Optional[datetime],
) -> bool:
    if todo_completed_at is None:
        return False
    return participation_created_at > todo_completed_at


def resolve_row_primary_status(stored_primary_status: str | None) -> str:
    if stored_primary_status is None:
        return WorklistDisplayStatus.NOT_STARTED
    return WorklistDisplayStatus(stored_primary_status)

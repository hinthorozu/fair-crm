from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class FollowUpRow:
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
class FollowUpListResult:
    items: list[FollowUpRow]
    page: int
    page_size: int
    total: int
    total_pages: int

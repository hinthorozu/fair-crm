from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.modules.todos.domain.exceptions import InvalidWorklistPrimaryStatusError
from app.modules.todos.domain.worklist_value_objects import StoredWorklistPrimaryStatus


def _validate_stored_primary_status(value: str) -> str:
    try:
        return StoredWorklistPrimaryStatus(value)
    except ValueError as exc:
        raise InvalidWorklistPrimaryStatusError(
            f"Invalid worklist primary status: {value}"
        ) from exc


@dataclass
class TodoWorklistState:
    id: UUID
    organization_id: UUID
    todo_id: UUID
    customer_id: UUID
    participation_id: Optional[UUID]
    primary_status: str
    last_activity_id: Optional[UUID]
    last_outcome_id: Optional[UUID]
    follow_up_at: Optional[datetime]
    last_note_summary: Optional[str]
    last_activity_at: Optional[datetime]
    last_actor_user_id: Optional[UUID]
    action_required: bool
    data_problem: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        todo_id: UUID,
        customer_id: UUID,
        primary_status: str,
        now: datetime,
        participation_id: Optional[UUID] = None,
        last_activity_id: Optional[UUID] = None,
        last_outcome_id: Optional[UUID] = None,
        follow_up_at: Optional[datetime] = None,
        last_note_summary: Optional[str] = None,
        last_activity_at: Optional[datetime] = None,
        last_actor_user_id: Optional[UUID] = None,
        action_required: bool = False,
        data_problem: bool = False,
    ) -> "TodoWorklistState":
        return cls(
            id=uuid4(),
            organization_id=organization_id,
            todo_id=todo_id,
            customer_id=customer_id,
            participation_id=participation_id,
            primary_status=_validate_stored_primary_status(primary_status),
            last_activity_id=last_activity_id,
            last_outcome_id=last_outcome_id,
            follow_up_at=follow_up_at,
            last_note_summary=last_note_summary.strip() if last_note_summary else None,
            last_activity_at=last_activity_at,
            last_actor_user_id=last_actor_user_id,
            action_required=action_required,
            data_problem=data_problem,
            created_at=now,
            updated_at=now,
        )

    def update_primary_status(self, *, primary_status: str, now: datetime) -> None:
        self.primary_status = _validate_stored_primary_status(primary_status)
        self.updated_at = now

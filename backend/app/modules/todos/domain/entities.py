from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.modules.todos.domain.exceptions import (
    InvalidTodoCategoryError,
    InvalidTodoPriorityError,
    InvalidTodoStatusError,
    InvalidTodoStatusTransitionError,
    InvalidTodoTitleError,
    TodoSourceFairChangeNotAllowedError,
)
from app.modules.todos.domain.value_objects import TodoCategory, TodoPriority, TodoStatus

PATCHABLE_STATUSES = frozenset(
    {
        TodoStatus.TODO,
        TodoStatus.IN_PROGRESS,
        TodoStatus.CANCELLED,
    }
)


def _validate_status(value: str) -> str:
    try:
        return TodoStatus(value)
    except ValueError as exc:
        raise InvalidTodoStatusError(f"Invalid todo status: {value}") from exc


def _validate_priority(value: str) -> str:
    try:
        return TodoPriority(value)
    except ValueError as exc:
        raise InvalidTodoPriorityError(f"Invalid todo priority: {value}") from exc


def _validate_category(value: str) -> str:
    try:
        return TodoCategory(value)
    except ValueError as exc:
        raise InvalidTodoCategoryError(f"Invalid todo category: {value}") from exc


@dataclass
class Todo:
    id: UUID
    organization_id: UUID
    title: str
    description: Optional[str]
    status: str
    priority: str
    category: str
    deadline: Optional[datetime]
    assignee_user_id: Optional[UUID]
    source_fair_id: Optional[UUID]
    created_by: UUID
    updated_by: Optional[UUID]
    archived_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        title: str,
        created_by: UUID,
        description: Optional[str] = None,
        status: str = TodoStatus.TODO,
        priority: str = TodoPriority.NORMAL,
        category: str = TodoCategory.GENEL_GOREV,
        deadline: Optional[datetime] = None,
        assignee_user_id: Optional[UUID] = None,
        source_fair_id: Optional[UUID] = None,
        now: datetime,
    ) -> "Todo":
        trimmed_title = title.strip()
        if not trimmed_title:
            raise InvalidTodoTitleError("title must not be empty")

        return cls(
            id=uuid4(),
            organization_id=organization_id,
            title=trimmed_title,
            description=description.strip() if description else None,
            status=_validate_status(status),
            priority=_validate_priority(priority),
            category=_validate_category(category),
            deadline=deadline,
            assignee_user_id=assignee_user_id,
            source_fair_id=source_fair_id,
            created_by=created_by,
            updated_by=None,
            archived_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )

    def update_fields(
        self,
        *,
        now: datetime,
        updated_by: UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        deadline: Optional[datetime] = None,
        assignee_user_id: Optional[UUID] = None,
        set_description: bool = False,
        set_deadline: bool = False,
        set_assignee_user_id: bool = False,
        source_fair_id: Optional[UUID] = None,
        set_source_fair_id: bool = False,
        has_worklist_states: bool = False,
    ) -> None:
        if title is not None:
            trimmed = title.strip()
            if not trimmed:
                raise InvalidTodoTitleError("title must not be empty")
            self.title = trimmed

        if set_description:
            self.description = description.strip() if description else None

        if status is not None:
            validated = _validate_status(status)
            if validated not in PATCHABLE_STATUSES:
                raise InvalidTodoStatusTransitionError(
                    "status done and archived must use dedicated action endpoints"
                )
            self.status = validated

        if priority is not None:
            self.priority = _validate_priority(priority)

        if category is not None:
            self.category = _validate_category(category)

        if set_deadline:
            self.deadline = deadline

        if set_assignee_user_id:
            self.assignee_user_id = assignee_user_id

        if set_source_fair_id:
            self.ensure_source_fair_change_allowed(
                new_source_fair_id=source_fair_id,
                has_worklist_states=has_worklist_states,
            )
            self.source_fair_id = source_fair_id

        self.updated_by = updated_by
        self.updated_at = now

    def ensure_source_fair_change_allowed(
        self,
        *,
        new_source_fair_id: Optional[UUID],
        has_worklist_states: bool,
    ) -> None:
        if new_source_fair_id == self.source_fair_id:
            return
        if self.status == TodoStatus.DONE:
            raise TodoSourceFairChangeNotAllowedError(
                "source_fair_id cannot change on a completed todo"
            )
        if has_worklist_states:
            raise TodoSourceFairChangeNotAllowedError(
                "source_fair_id cannot change after worklist state exists"
            )

    def complete(self, *, now: datetime, updated_by: UUID) -> None:
        self.status = TodoStatus.DONE
        self.completed_at = now
        self.updated_by = updated_by
        self.updated_at = now

    def archive(self, *, now: datetime, updated_by: UUID) -> None:
        self.status = TodoStatus.ARCHIVED
        self.archived_at = now
        self.updated_by = updated_by
        self.updated_at = now

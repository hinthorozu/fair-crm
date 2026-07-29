"""Todo checklist step domain entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from app.modules.todos.domain.exceptions import InvalidTodoStepTitleError


@dataclass
class TodoStep:
    id: UUID
    organization_id: UUID
    todo_id: UUID
    title: str
    sort_order: int
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        todo_id: UUID,
        title: str,
        sort_order: int,
        now: datetime,
        is_completed: bool = False,
    ) -> TodoStep:
        cleaned = title.strip()
        if not cleaned:
            raise InvalidTodoStepTitleError("Step title is required")
        if len(cleaned) > 500:
            raise InvalidTodoStepTitleError("Step title is too long")
        return cls(
            id=uuid4(),
            organization_id=organization_id,
            todo_id=todo_id,
            title=cleaned,
            sort_order=sort_order,
            is_completed=is_completed,
            created_at=now,
            updated_at=now,
        )

    def rename(self, *, title: str, now: datetime) -> None:
        cleaned = title.strip()
        if not cleaned:
            raise InvalidTodoStepTitleError("Step title is required")
        if len(cleaned) > 500:
            raise InvalidTodoStepTitleError("Step title is too long")
        self.title = cleaned
        self.updated_at = now

    def set_completed(self, *, is_completed: bool, now: datetime) -> None:
        self.is_completed = is_completed
        self.updated_at = now

    def set_sort_order(self, *, sort_order: int, now: datetime) -> None:
        self.sort_order = sort_order
        self.updated_at = now

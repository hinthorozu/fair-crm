from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class TodoStepResult:
    id: UUID
    organization_id: UUID
    todo_id: UUID
    title: str
    sort_order: int
    is_completed: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class TodoStepReplaceItem:
    id: UUID | None
    title: str


@dataclass(frozen=True)
class ListTodoStepsQuery:
    organization_id: UUID
    access_token: str
    user_id: UUID
    todo_id: UUID


@dataclass(frozen=True)
class ReplaceTodoStepsCommand:
    organization_id: UUID
    access_token: str
    user_id: UUID
    todo_id: UUID
    steps: list[TodoStepReplaceItem]


@dataclass(frozen=True)
class UpdateTodoStepCommand:
    organization_id: UUID
    access_token: str
    user_id: UUID
    todo_id: UUID
    step_id: UUID
    title: str | None = None
    is_completed: bool | None = None
    set_title: bool = False
    set_is_completed: bool = False


@dataclass(frozen=True)
class DeleteTodoStepCommand:
    organization_id: UUID
    access_token: str
    user_id: UUID
    todo_id: UUID
    step_id: UUID

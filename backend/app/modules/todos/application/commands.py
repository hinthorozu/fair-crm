from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class CreateTodoCommand:
    organization_id: UUID
    access_token: str
    user_id: UUID
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "normal"
    category: str = "genel_gorev"
    deadline: Optional[datetime] = None
    assignee_user_id: Optional[UUID] = None


@dataclass(frozen=True)
class GetTodoQuery:
    organization_id: UUID
    todo_id: UUID


@dataclass(frozen=True)
class ListTodosQuery:
    organization_id: UUID
    search: str | None = None
    status: str | None = None
    priority: str | None = None
    category: str | None = None
    assignee_user_id: UUID | None = None
    created_by: UUID | None = None
    is_overdue: bool | None = None
    include_archived: bool = False
    page: int = 1
    page_size: int = 25
    sort_by: str = "updated_at"
    sort_dir: str = "desc"


@dataclass(frozen=True)
class UpdateTodoCommand:
    organization_id: UUID
    todo_id: UUID
    access_token: str
    user_id: UUID
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    deadline: Optional[datetime] = None
    assignee_user_id: Optional[UUID] = None
    set_description: bool = False
    set_deadline: bool = False
    set_assignee_user_id: bool = False


@dataclass(frozen=True)
class CompleteTodoCommand:
    organization_id: UUID
    todo_id: UUID
    access_token: str
    user_id: UUID


@dataclass(frozen=True)
class ArchiveTodoCommand:
    organization_id: UUID
    todo_id: UUID
    access_token: str
    user_id: UUID


@dataclass(frozen=True)
class DeleteTodoCommand:
    organization_id: UUID
    todo_id: UUID
    access_token: str
    user_id: UUID


@dataclass(frozen=True)
class TodoResult:
    id: UUID
    organization_id: UUID
    title: str
    description: Optional[str]
    status: str
    priority: str
    category: str
    deadline: Optional[datetime]
    assignee_user_id: Optional[UUID]
    created_by: UUID
    updated_by: Optional[UUID]
    archived_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    is_overdue: bool


@dataclass(frozen=True)
class TodoListResultDto:
    items: list[TodoResult]
    page: int
    page_size: int
    total: int
    total_pages: int

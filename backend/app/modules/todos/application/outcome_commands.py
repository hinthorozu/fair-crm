from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class TodoOutcomeResult:
    id: UUID
    organization_id: UUID
    name: str
    code: str
    description: Optional[str]
    is_active: bool
    sort_order: int
    primary_worklist_status: str
    requires_action: bool
    marks_data_problem: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class TodoOutcomeListResultDto:
    items: list[TodoOutcomeResult]
    page: int
    page_size: int
    total: int
    total_pages: int


@dataclass(frozen=True)
class ListTodoOutcomesQuery:
    organization_id: UUID
    is_active: bool | None = None
    search: str | None = None
    page: int = 1
    page_size: int = 100
    sort_by: str = "sort_order"
    sort_dir: str = "asc"
    ensure_defaults: bool = True


@dataclass(frozen=True)
class GetTodoOutcomeQuery:
    organization_id: UUID
    outcome_id: UUID


@dataclass(frozen=True)
class CreateTodoOutcomeCommand:
    organization_id: UUID
    access_token: str
    user_id: UUID
    name: str
    code: str
    primary_worklist_status: str
    description: Optional[str] = None
    sort_order: int = 0
    requires_action: bool = False
    marks_data_problem: bool = False
    is_active: bool = True


@dataclass(frozen=True)
class UpdateTodoOutcomeCommand:
    organization_id: UUID
    outcome_id: UUID
    access_token: str
    user_id: UUID
    name: Optional[str] = None
    description: Optional[str] = None
    primary_worklist_status: Optional[str] = None
    requires_action: Optional[bool] = None
    marks_data_problem: Optional[bool] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    set_description: bool = False


@dataclass(frozen=True)
class DeactivateTodoOutcomeCommand:
    organization_id: UUID
    outcome_id: UUID
    access_token: str
    user_id: UUID


@dataclass(frozen=True)
class EnsureDefaultOutcomesCommand:
    organization_id: UUID

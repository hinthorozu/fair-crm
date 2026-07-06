from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.modules.todos.domain.entities import Todo


@dataclass(frozen=True)
class TodoListResult:
    items: list[Todo]
    page: int
    page_size: int
    total: int
    total_pages: int


class TodoRepository(Protocol):
    def add(self, todo: Todo) -> Todo: ...

    def get_by_id(self, organization_id: UUID, todo_id: UUID) -> Todo | None: ...

    def update(self, todo: Todo) -> Todo: ...

    def list_by_organization(
        self,
        organization_id: UUID,
        *,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "updated_at",
        sort_dir: str = "desc",
        exclude_archived: bool = True,
    ) -> TodoListResult: ...

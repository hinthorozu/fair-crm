from dataclasses import dataclass
from typing import Any, Optional, Protocol
from uuid import UUID

from app.modules.operations.domain.entities import Operation, OperationRun, OperationRunItem


@dataclass
class OperationListResult:
    items: list[Operation]
    page: int
    page_size: int
    total: int
    total_pages: int


@dataclass
class OperationRunListResult:
    items: list[OperationRun]
    page: int
    page_size: int
    total: int
    total_pages: int


@dataclass
class OperationRunItemListResult:
    items: list[OperationRunItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class OperationRepository(Protocol):
    def add(self, operation: Operation) -> Operation: ...

    def get_by_id(self, organization_id: UUID, operation_id: UUID) -> Operation | None: ...

    def update(self, operation: Operation) -> Operation: ...

    def list_by_organization(
        self,
        organization_id: UUID,
        *,
        operation_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> OperationListResult: ...


class OperationRunRepository(Protocol):
    def add(self, run: OperationRun) -> OperationRun: ...

    def get_by_id(self, organization_id: UUID, run_id: UUID) -> OperationRun | None: ...

    def update(self, run: OperationRun) -> OperationRun: ...

    def list_by_operation(
        self,
        organization_id: UUID,
        operation_id: UUID,
        *,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> OperationRunListResult: ...


class OperationRunItemRepository(Protocol):
    def add(self, item: OperationRunItem) -> OperationRunItem: ...

    def add_many(self, items: list[OperationRunItem]) -> list[OperationRunItem]: ...

    def get_by_id(
        self, organization_id: UUID, item_id: UUID
    ) -> OperationRunItem | None: ...

    def update(self, item: OperationRunItem) -> OperationRunItem: ...

    def list_by_run(
        self,
        organization_id: UUID,
        run_id: UUID,
        *,
        status: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_dir: str = "asc",
    ) -> OperationRunItemListResult: ...

from dataclasses import dataclass
from datetime import datetime

from app.modules.operations.infrastructure.repositories.operation_type_repository import (
    SqlAlchemyOperationTypeRepository,
    capabilities_from_model,
)


@dataclass(frozen=True)
class OperationTypeListItem:
    key: str
    name: str
    is_active: bool
    sort_order: int
    supports_pause: bool
    supports_resume: bool
    supports_retry: bool
    supports_schedule: bool
    supports_items: bool
    updated_at: datetime


@dataclass(frozen=True)
class OperationTypeListResult:
    items: list[OperationTypeListItem]


class ListOperationTypesUseCase:
    def __init__(self, repository: SqlAlchemyOperationTypeRepository) -> None:
        self._repository = repository

    def execute(self, *, active_only: bool = False) -> OperationTypeListResult:
        rows = self._repository.list_types(active_only=active_only)
        items: list[OperationTypeListItem] = []
        for row in rows:
            caps = capabilities_from_model(row)
            items.append(
                OperationTypeListItem(
                    key=row.key,
                    name=row.name,
                    is_active=row.is_active,
                    sort_order=row.sort_order,
                    supports_pause=caps.supports_pause,
                    supports_resume=caps.supports_resume,
                    supports_retry=caps.supports_retry,
                    supports_schedule=caps.supports_schedule,
                    supports_items=caps.supports_items,
                    updated_at=row.updated_at,
                )
            )
        return OperationTypeListResult(items=items)

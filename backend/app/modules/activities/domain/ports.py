from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.activities.domain.entities import Activity


@dataclass(frozen=True)
class ActivityListResult:
    items: list[Activity]
    page: int
    page_size: int
    total: int
    total_pages: int


class ActivityRepository(Protocol):
    def add(self, activity: Activity) -> Activity: ...

    def get_by_id(self, organization_id: UUID, activity_id: UUID) -> Activity | None: ...

    def update(self, activity: Activity) -> Activity: ...

    def hard_delete(self, organization_id: UUID, activity_id: UUID) -> bool: ...

    def hard_delete_many(self, organization_id: UUID, activity_ids: list[UUID]) -> int: ...

    def get_existing_ids(
        self, organization_id: UUID, activity_ids: list[UUID]
    ) -> list[UUID]: ...

    def list_by_customer(
        self,
        organization_id: UUID,
        customer_id: UUID,
        *,
        search: str | None = None,
        activity_type: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "activity_date",
        sort_dir: str = "desc",
        include_deleted: bool = False,
    ) -> ActivityListResult: ...

    def list_all(
        self,
        organization_id: UUID,
        *,
        search: str | None = None,
        customer_id: UUID | None = None,
        activity_type: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "activity_date",
        sort_dir: str = "desc",
        include_deleted: bool = False,
    ) -> ActivityListResult: ...

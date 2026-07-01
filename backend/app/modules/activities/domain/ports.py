from dataclasses import dataclass
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

    def list_by_customer(
        self,
        organization_id: UUID,
        customer_id: UUID,
        *,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "activity_date",
        sort_dir: str = "desc",
        include_deleted: bool = False,
    ) -> ActivityListResult: ...

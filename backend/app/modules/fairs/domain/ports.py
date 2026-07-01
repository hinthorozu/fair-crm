from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.value_objects import FairStatus


@dataclass
class FairListResult:
    items: list[Fair]
    page: int
    page_size: int
    total: int
    total_pages: int


class FairRepository(Protocol):
    def add(self, fair: Fair) -> Fair: ...

    def get_by_id(self, organization_id: UUID, fair_id: UUID) -> Fair | None: ...

    def get_by_id_including_archived(
        self, organization_id: UUID, fair_id: UUID
    ) -> Fair | None: ...

    def update(self, fair: Fair) -> Fair: ...

    def list_by_organization(
        self,
        organization_id: UUID,
        *,
        status: FairStatus | None = None,
        include_archived: bool = False,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> FairListResult: ...

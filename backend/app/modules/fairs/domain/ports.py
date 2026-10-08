from dataclasses import dataclass
from datetime import date
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

    def get_visible(self, organization_id: UUID, fair_id: UUID) -> Fair | None: ...

    def get_visible_including_archived(
        self, organization_id: UUID, fair_id: UUID
    ) -> Fair | None: ...

    def update(self, fair: Fair) -> Fair: ...

    def list_by_organization(
        self,
        organization_id: UUID,
        *,
        status: FairStatus | None = None,
        include_archived: bool = False,
        country: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "start_date",
        sort_dir: str = "desc",
    ) -> FairListResult: ...

    def list_visible(
        self,
        organization_id: UUID,
        *,
        status: FairStatus | None = None,
        include_archived: bool = False,
        country: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "start_date",
        sort_dir: str = "desc",
        default_date_order: bool = False,
        today: date | None = None,
    ) -> FairListResult: ...

    def get_system_fair_by_external_id(self, *, source: str, external_id: str) -> Fair | None: ...

    def list_system_fairs_for_source(self, *, source: str) -> list[Fair]: ...

    def list_system_fair_separation_ids(self, *, source: str) -> set[UUID]: ...

    def update_system_fair(self, fair: Fair) -> Fair: ...

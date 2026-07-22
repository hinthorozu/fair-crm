from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from app.modules.participations.domain.entities import CustomerFairParticipation


@dataclass
class ParticipationListResult:
    items: list[CustomerFairParticipation]
    page: int
    page_size: int
    total: int
    total_pages: int


@dataclass
class CustomerParticipationRow:
    participation: CustomerFairParticipation
    fair_name: str
    fair_start_date: date | None
    fair_end_date: date | None


@dataclass
class CustomerParticipationListResult:
    items: list[CustomerParticipationRow]
    page: int
    page_size: int
    total: int
    total_pages: int


@dataclass
class FairParticipantRow:
    participation: CustomerFairParticipation
    company_name: str
    email: str | None
    phone: str | None
    country: str | None
    city: str | None


@dataclass
class FairParticipantListResult:
    items: list[FairParticipantRow]
    page: int
    page_size: int
    total: int
    total_pages: int


class ParticipationRepository(Protocol):
    def add(self, participation: CustomerFairParticipation) -> CustomerFairParticipation: ...

    def get_by_id(self, organization_id: UUID, participation_id: UUID) -> CustomerFairParticipation | None: ...

    def update(self, participation: CustomerFairParticipation) -> CustomerFairParticipation: ...

    def exists_active(
        self, organization_id: UUID, customer_id: UUID, fair_id: UUID
    ) -> bool: ...

    def list_by_customer(
        self,
        organization_id: UUID,
        customer_id: UUID,
        *,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "fair_start_date",
        sort_dir: str = "desc",
    ) -> CustomerParticipationListResult: ...

    def list_by_fair(
        self,
        organization_id: UUID,
        fair_id: UUID,
        *,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "company_name",
        sort_dir: str = "asc",
    ) -> FairParticipantListResult: ...

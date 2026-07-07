from dataclasses import dataclass
from uuid import UUID

from app.modules.dashboard.domain.summary import DashboardSummary
from app.modules.dashboard.infrastructure.repositories.dashboard_query_repository import (
    SqlAlchemyDashboardQueryRepository,
)

PERMISSION_READ = "fair_crm.dashboard.read"


@dataclass(frozen=True)
class GetDashboardSummaryQuery:
    organization_id: UUID


class GetDashboardSummaryUseCase:
    def __init__(self, repository: SqlAlchemyDashboardQueryRepository) -> None:
        self._repository = repository

    def execute(self, query: GetDashboardSummaryQuery) -> DashboardSummary:
        return self._repository.get_summary(query.organization_id)

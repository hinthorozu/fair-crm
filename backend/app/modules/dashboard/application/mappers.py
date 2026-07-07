from app.modules.dashboard.api.schemas import (
    DashboardFairSummaryResponse,
    DashboardMailStatusSummaryResponse,
    DashboardOverviewCardsResponse,
    DashboardRecentActivityResponse,
    DashboardSummaryResponse,
    DashboardTaskSummaryResponse,
)
from app.modules.dashboard.domain.summary import DashboardSummary


def dashboard_summary_to_response(summary: DashboardSummary) -> DashboardSummaryResponse:
    """Build API response using snake_case field names (Pydantic input contract)."""
    return DashboardSummaryResponse(
        overview=DashboardOverviewCardsResponse.model_validate(summary.overview),
        task_summary=DashboardTaskSummaryResponse.model_validate(summary.task_summary),
        recent_activities=[
            DashboardRecentActivityResponse.model_validate(item)
            for item in summary.recent_activities
        ],
        fair_summaries=[
            DashboardFairSummaryResponse.model_validate(item) for item in summary.fair_summaries
        ],
        mail_status=DashboardMailStatusSummaryResponse.model_validate(summary.mail_status),
    )

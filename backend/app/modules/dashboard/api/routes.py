"""Dashboard summary API."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.integrations.kyrox_core.auth import AuthContext
from app.modules.dashboard.api.dependencies import get_dashboard_summary_use_case, require_read_permission
from app.modules.dashboard.api.schemas import DashboardSummaryResponse
from app.modules.dashboard.application.get_dashboard_summary import (
    GetDashboardSummaryQuery,
    GetDashboardSummaryUseCase,
)
from app.modules.dashboard.application.mappers import dashboard_summary_to_response

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    response_model_by_alias=True,
    summary="Dashboard özet verisi",
)
def get_dashboard_summary(
    auth: Annotated[AuthContext, Depends(require_read_permission)],
    use_case: Annotated[GetDashboardSummaryUseCase, Depends(get_dashboard_summary_use_case)],
) -> DashboardSummaryResponse:
    summary = use_case.execute(GetDashboardSummaryQuery(organization_id=auth.organization_id))
    return dashboard_summary_to_response(summary)

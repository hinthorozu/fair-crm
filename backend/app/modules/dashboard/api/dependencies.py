from uuid import UUID

import httpx
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.client import KyroxCoreHttpClient
from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled, resolve_auth_context
from app.modules.dashboard.application.get_dashboard_summary import GetDashboardSummaryUseCase
from app.modules.dashboard.infrastructure.repositories.dashboard_query_repository import (
    SqlAlchemyDashboardQueryRepository,
)

bearer_scheme = HTTPBearer(auto_error=False)


def get_core_http_client() -> KyroxCoreHttpClient:
    return KyroxCoreHttpClient()


def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    organization_id: UUID = Header(..., alias="X-Organization-Id"),
    dev_user_id: UUID | None = Header(default=None, alias="X-Dev-User-Id"),
) -> AuthContext:
    try:
        return resolve_auth_context(credentials, organization_id, dev_user_id=dev_user_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated") from exc


def require_dashboard_access(
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    core_http: KyroxCoreHttpClient = Depends(get_core_http_client),
) -> AuthContext:
    """Require login plus active access to the selected organization; no RBAC permission."""
    if dev_bypass_enabled():
        return auth
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        response = core_http.request(
            "GET",
            f"/api/v1/organizations/{auth.organization_id}/access/verify",
            access_token=credentials.credentials,
            organization_id=auth.organization_id,
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Organization access service unavailable",
        ) from exc

    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if response.status_code == status.HTTP_403_FORBIDDEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied")
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Organization access check failed",
        )

    return auth


def get_dashboard_summary_use_case(
    db: Session = Depends(get_db),
) -> GetDashboardSummaryUseCase:
    return GetDashboardSummaryUseCase(SqlAlchemyDashboardQueryRepository(db))

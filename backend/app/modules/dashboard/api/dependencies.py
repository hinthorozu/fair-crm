from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.client import HttpAuthorizationAdapter
from app.integrations.kyrox_core.dev_bypass import (
    AllowAllAuthorizationAdapter,
    dev_bypass_enabled,
    resolve_auth_context,
)
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.dashboard.application.get_dashboard_summary import (
    PERMISSION_READ,
    GetDashboardSummaryUseCase,
)
from app.modules.dashboard.infrastructure.repositories.dashboard_query_repository import (
    SqlAlchemyDashboardQueryRepository,
)

bearer_scheme = HTTPBearer(auto_error=False)


def get_authorization_adapter() -> AuthorizationPort:
    if dev_bypass_enabled():
        return AllowAllAuthorizationAdapter()
    return HttpAuthorizationAdapter()


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


def require_read_permission(
    auth: AuthContext = Depends(get_auth_context),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthContext:
    if dev_bypass_enabled():
        return auth
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not authorization.check_permission(
        organization_id=auth.organization_id,
        user_id=auth.user_id,
        permission_code=PERMISSION_READ,
        access_token=credentials.credentials,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return auth


def get_dashboard_summary_use_case(
    db: Session = Depends(get_db),
) -> GetDashboardSummaryUseCase:
    return GetDashboardSummaryUseCase(SqlAlchemyDashboardQueryRepository(db))

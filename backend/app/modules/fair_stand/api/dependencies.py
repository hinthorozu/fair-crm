from collections.abc import Sequence

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.dashboard.api.dependencies import require_dashboard_access
from app.modules.fair_stand.application.admin_catalog import AdminCatalogService
from app.modules.fair_stand.application.get_catalog_bootstrap import GetCatalogBootstrapUseCase
from app.modules.fair_stand.application.get_item import GetItemUseCase
from app.modules.fair_stand.infrastructure.catalog_repository import SqlAlchemyFairStandCatalogRepository
from app.modules.mail_templates.api.dependencies import (
    bearer_scheme,
    get_auth_context,
    get_authorization_adapter,
)

require_fair_stand_catalog_access = require_dashboard_access

PERMISSION_CATALOG_READ = "fair_crm.admin.fair_stand.catalog.read"
PERMISSION_CATALOG_CREATE = "fair_crm.admin.fair_stand.catalog.create"
PERMISSION_CATALOG_UPDATE = "fair_crm.admin.fair_stand.catalog.update"
PERMISSION_CATALOG_ARCHIVE = "fair_crm.admin.fair_stand.catalog.archive"
PERMISSION_PREVIEWS_READ = "fair_crm.admin.fair_stand.previews.read"
PERMISSION_PREVIEWS_CREATE = "fair_crm.admin.fair_stand.previews.create"
PERMISSION_PREVIEWS_UPDATE = "fair_crm.admin.fair_stand.previews.update"
PERMISSION_PREVIEWS_ARCHIVE = "fair_crm.admin.fair_stand.previews.archive"


def get_catalog_repository(db: Session = Depends(get_db)) -> SqlAlchemyFairStandCatalogRepository:
    return SqlAlchemyFairStandCatalogRepository(db)


def get_catalog_bootstrap_use_case(
    repository: SqlAlchemyFairStandCatalogRepository = Depends(get_catalog_repository),
) -> GetCatalogBootstrapUseCase:
    return GetCatalogBootstrapUseCase(repository)


def get_item_use_case(
    repository: SqlAlchemyFairStandCatalogRepository = Depends(get_catalog_repository),
) -> GetItemUseCase:
    return GetItemUseCase(repository)


def get_admin_catalog_service(
    db: Session = Depends(get_db),
    repository: SqlAlchemyFairStandCatalogRepository = Depends(get_catalog_repository),
) -> AdminCatalogService:
    return AdminCatalogService(session=db, repository=repository)


def _require_any_permission(permission_codes: Sequence[str]):
    def dependency(
        auth: AuthContext = Depends(get_auth_context),
        authorization: AuthorizationPort = Depends(get_authorization_adapter),
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> AuthContext:
        if dev_bypass_enabled():
            return auth
        if credentials is None or not credentials.credentials:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        if not any(
            authorization.check_permission(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                permission_code=permission_code,
                access_token=credentials.credentials,
            )
            for permission_code in permission_codes
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return auth

    return dependency


def require_permission(permission_code: str):
    return _require_any_permission((permission_code,))


def require_any_permission(*permission_codes: str):
    if not permission_codes:
        raise ValueError("At least one permission code is required")
    return _require_any_permission(permission_codes)

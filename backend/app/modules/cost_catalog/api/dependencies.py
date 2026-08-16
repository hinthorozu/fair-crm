from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.mail_templates.api.dependencies import (
    bearer_scheme,
    get_auth_context,
    get_authorization_adapter,
)

CATEGORY_VIEW = "fair_crm.cost_catalog.categories.read"
CATEGORY_CREATE = "fair_crm.cost_catalog.categories.create"
CATEGORY_UPDATE = "fair_crm.cost_catalog.categories.update"
CATEGORY_DELETE = "fair_crm.cost_catalog.categories.delete"
PRODUCT_VIEW = "fair_crm.cost_catalog.products.read"
PRODUCT_CREATE = "fair_crm.cost_catalog.products.create"
PRODUCT_UPDATE = "fair_crm.cost_catalog.products.update"
PRODUCT_DELETE = "fair_crm.cost_catalog.products.delete"


def require_permission(permission_code: str):
    def dependency(
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
            permission_code=permission_code,
            access_token=credentials.credentials,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return auth

    return dependency

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

PERMISSION_READ = "fair_crm.quote_templates.read"
PERMISSION_CREATE = "fair_crm.quote_templates.create"
PERMISSION_UPDATE = "fair_crm.quote_templates.update"


def _require(permission_code: str):
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


require_read_permission = _require(PERMISSION_READ)
require_create_permission = _require(PERMISSION_CREATE)
require_update_permission = _require(PERMISSION_UPDATE)

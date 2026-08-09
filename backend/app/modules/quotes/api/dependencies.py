from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.activities.api.dependencies import (
    bearer_scheme,
    get_auth_context,
    get_authorization_adapter,
)


def _require(code: str):
    def dependency(
        auth: AuthContext = Depends(get_auth_context),
        authorization: AuthorizationPort = Depends(get_authorization_adapter),
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> AuthContext:
        token = credentials.credentials if credentials else "dev-bypass"
        if not authorization.check_permission(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            permission_code=code,
            access_token=token,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return auth
    return dependency


require_read_permission = _require("fair_crm.quotes.read")
require_create_permission = _require("fair_crm.quotes.create")
require_update_permission = _require("fair_crm.quotes.update")
require_delete_permission = _require("fair_crm.quotes.delete")

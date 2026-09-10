from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.lifecycle import OrganizationLifecycleGuard
from app.integrations.kyrox_core.ports import AuditPort, AuthContext, AuthorizationPort
from app.integrations.kyrox_core.tombstone import KyroxCoreOrganizationTombstoneAdapter
from app.modules.organization_closure.api.routes import (
    _access_token,
    _assert_target_context,
    _raise_http_error,
    get_closure_auth_context,
    get_lifecycle_guard,
)
from app.modules.organization_closure.api.schemas import OrganizationClosureExecutionResponse
from app.modules.organization_closure.application.service import OrganizationClosureError
from app.modules.organization_closure.application.terminal_closure import (
    OrganizationClosureTerminalService,
)
from app.modules.organization_closure.infrastructure.product_cleanup_repository import (
    SqlAlchemyOrganizationClosureProductCleanupRepository,
)
from app.modules.organization_closure.infrastructure.repository import (
    SqlAlchemyOrganizationClosureRepository,
)
from app.modules.system_admin.api.dependencies import (
    bearer_scheme,
    get_audit_adapter,
    get_authorization_adapter,
)

router = APIRouter(prefix="/system-admin", tags=["system-admin"])


def get_tombstone_adapter() -> KyroxCoreOrganizationTombstoneAdapter:
    return KyroxCoreOrganizationTombstoneAdapter()


def get_terminal_closure_service(
    db: Session = Depends(get_db),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    lifecycle: OrganizationLifecycleGuard = Depends(get_lifecycle_guard),
    tombstone: KyroxCoreOrganizationTombstoneAdapter = Depends(get_tombstone_adapter),
    audit: AuditPort = Depends(get_audit_adapter),
) -> OrganizationClosureTerminalService:
    return OrganizationClosureTerminalService(
        SqlAlchemyOrganizationClosureProductCleanupRepository(db),
        SqlAlchemyOrganizationClosureRepository(db),
        authorization,
        lifecycle,
        tombstone,
        audit,
    )


@router.post(
    "/organizations/{organization_id}/closure-executions/{execution_id}/finalize",
    response_model=OrganizationClosureExecutionResponse,
)
def finalize_organization_closure(
    organization_id: UUID,
    execution_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: OrganizationClosureTerminalService = Depends(get_terminal_closure_service),
) -> OrganizationClosureExecutionResponse:
    _assert_target_context(auth, organization_id)
    try:
        execution = service.finalize(
            organization_id=organization_id,
            execution_id=execution_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return OrganizationClosureExecutionResponse.model_validate(execution)

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.lifecycle import OrganizationLifecycleGuard
from app.integrations.kyrox_core.ports import AuditPort, AuthContext, AuthorizationPort
from app.modules.organization_closure.api.routes import (
    _access_token,
    _assert_target_context,
    _raise_http_error,
    get_closure_auth_context,
    get_lifecycle_guard,
)
from app.modules.organization_closure.api.schemas import (
    OrganizationClosureProductCleanupItemResponse,
    OrganizationClosureProductCleanupResponse,
)
from app.modules.organization_closure.application.product_cleanup import (
    OrganizationClosureProductCleanupService,
)
from app.modules.organization_closure.application.service import OrganizationClosureError
from app.modules.organization_closure.infrastructure.product_cleanup_repository import (
    SqlAlchemyOrganizationClosureProductCleanupRepository,
)
from app.modules.system_admin.api.dependencies import (
    bearer_scheme,
    get_audit_adapter,
    get_authorization_adapter,
)

router = APIRouter(prefix="/system-admin", tags=["system-admin"])


def get_product_cleanup_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyOrganizationClosureProductCleanupRepository:
    return SqlAlchemyOrganizationClosureProductCleanupRepository(db)


def get_product_cleanup_service(
    repository: SqlAlchemyOrganizationClosureProductCleanupRepository = Depends(
        get_product_cleanup_repository
    ),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    lifecycle: OrganizationLifecycleGuard = Depends(get_lifecycle_guard),
    audit: AuditPort = Depends(get_audit_adapter),
) -> OrganizationClosureProductCleanupService:
    return OrganizationClosureProductCleanupService(
        repository,
        authorization,
        lifecycle,
        audit,
    )


def _response(result) -> OrganizationClosureProductCleanupResponse:
    return OrganizationClosureProductCleanupResponse(
        processed_class_key=result.processed_class_key,
        completed=result.completed,
        blocked=result.blocked,
        pending=result.pending,
        product_data_cleanup_complete=result.product_data_cleanup_complete,
        items=[
            OrganizationClosureProductCleanupItemResponse.model_validate(item)
            for item in result.items
        ],
    )


@router.post(
    "/organizations/{organization_id}/closure-executions/{execution_id}/product-data-cleanup/reconcile",
    response_model=OrganizationClosureProductCleanupResponse,
)
def reconcile_product_data_cleanup(
    organization_id: UUID,
    execution_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: OrganizationClosureProductCleanupService = Depends(
        get_product_cleanup_service
    ),
) -> OrganizationClosureProductCleanupResponse:
    _assert_target_context(auth, organization_id)
    try:
        result = service.reconcile(
            organization_id=organization_id,
            execution_id=execution_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return _response(result)


@router.get(
    "/organizations/{organization_id}/closure-executions/{execution_id}/product-data-cleanup",
    response_model=OrganizationClosureProductCleanupResponse,
)
def get_product_data_cleanup(
    organization_id: UUID,
    execution_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: OrganizationClosureProductCleanupService = Depends(
        get_product_cleanup_service
    ),
) -> OrganizationClosureProductCleanupResponse:
    _assert_target_context(auth, organization_id)
    try:
        result = service.get(
            organization_id=organization_id,
            execution_id=execution_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return _response(result)

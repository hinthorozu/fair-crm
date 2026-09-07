from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.lifecycle import OrganizationLifecycleGuard
from app.integrations.kyrox_core.ports import AuditPort, AuthContext, AuthorizationPort
from app.modules.organization_closure.api.schemas import OrganizationClosureExecutionResponse
from app.modules.organization_closure.application.service import (
    ClosureAuthorizationUnavailableError,
    ClosureExecutionConflictError,
    ClosureExecutionNotFoundError,
    ClosureLifecyclePreconditionError,
    ClosureLifecycleUnavailableError,
    ClosurePermissionDeniedError,
    OrganizationClosureError,
    OrganizationClosureService,
)
from app.modules.organization_closure.infrastructure.repository import (
    SqlAlchemyOrganizationClosureRepository,
)
from app.modules.system_admin.api.dependencies import (
    bearer_scheme,
    get_audit_adapter,
    get_auth_context,
    get_authorization_adapter,
)

router = APIRouter(prefix="/system-admin", tags=["system-admin"])


def get_closure_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyOrganizationClosureRepository:
    return SqlAlchemyOrganizationClosureRepository(db)


def get_lifecycle_guard() -> OrganizationLifecycleGuard:
    return OrganizationLifecycleGuard()


def get_closure_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_organization_id: UUID = Header(..., alias="X-Organization-Id"),
    dev_user_id: UUID | None = Header(default=None, alias="X-Dev-User-Id"),
) -> AuthContext:
    return get_auth_context(credentials, x_organization_id, dev_user_id)


def get_closure_service(
    repository: SqlAlchemyOrganizationClosureRepository = Depends(get_closure_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    lifecycle: OrganizationLifecycleGuard = Depends(get_lifecycle_guard),
    audit: AuditPort = Depends(get_audit_adapter),
) -> OrganizationClosureService:
    return OrganizationClosureService(repository, authorization, lifecycle, audit)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    return credentials.credentials if credentials and credentials.credentials else ""


def _assert_target_context(auth: AuthContext, organization_id: UUID) -> None:
    if auth.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization context mismatch",
        )


def _normalize_idempotency_key(value: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > 200:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Idempotency-Key must contain 1 to 200 non-whitespace characters",
        )
    return normalized


def _raise_http_error(exc: OrganizationClosureError) -> NoReturn:
    if isinstance(exc, ClosurePermissionDeniedError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, (ClosureAuthorizationUnavailableError, ClosureLifecycleUnavailableError)):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    if isinstance(exc, (ClosureLifecyclePreconditionError, ClosureExecutionConflictError)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, ClosureExecutionNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Closure error",
    ) from exc


@router.post(
    "/organizations/{organization_id}/closure-executions",
    response_model=OrganizationClosureExecutionResponse,
)
def start_closure_execution(
    organization_id: UUID,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: OrganizationClosureService = Depends(get_closure_service),
) -> OrganizationClosureExecutionResponse:
    _assert_target_context(auth, organization_id)
    try:
        execution = service.start(
            organization_id=organization_id,
            idempotency_key=_normalize_idempotency_key(idempotency_key),
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return OrganizationClosureExecutionResponse.model_validate(execution)


@router.get(
    "/organizations/{organization_id}/closure-executions/{execution_id}",
    response_model=OrganizationClosureExecutionResponse,
)
def get_closure_execution(
    organization_id: UUID,
    execution_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: OrganizationClosureService = Depends(get_closure_service),
) -> OrganizationClosureExecutionResponse:
    _assert_target_context(auth, organization_id)
    try:
        execution = service.get(
            organization_id=organization_id,
            execution_id=execution_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return OrganizationClosureExecutionResponse.model_validate(execution)


@router.post(
    "/organizations/{organization_id}/closure-executions/{execution_id}/retry",
    response_model=OrganizationClosureExecutionResponse,
)
def retry_closure_execution(
    organization_id: UUID,
    execution_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: OrganizationClosureService = Depends(get_closure_service),
) -> OrganizationClosureExecutionResponse:
    _assert_target_context(auth, organization_id)
    try:
        execution = service.retry(
            organization_id=organization_id,
            execution_id=execution_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return OrganizationClosureExecutionResponse.model_validate(execution)

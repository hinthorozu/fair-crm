from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.lifecycle import OrganizationLifecycleGuard
from app.integrations.kyrox_core.ports import AuditPort, AuthContext, AuthorizationPort
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)
from app.modules.organization_closure.api.schemas import (
    OrganizationClosureCredentialDispositionListResponse,
    OrganizationClosureCredentialDispositionResponse,
    OrganizationClosureCredentialReconcileRequest,
    OrganizationClosureExecutionResponse,
    OrganizationClosureExportPlanResponse,
)
from app.modules.organization_closure.application.credential_disposition import (
    OrganizationClosureCredentialDispositionService,
)
from app.modules.organization_closure.application.export_planner import (
    ClosureExportPlanningError,
    OrganizationClosureExportPlanner,
)
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
from app.modules.organization_closure.infrastructure.credential_disposition_repository import (
    SqlAlchemyOrganizationClosureCredentialDispositionRepository,
)
from app.modules.organization_closure.infrastructure.export_plan_repository import (
    SqlAlchemyOrganizationClosureExportPlanRepository,
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


def get_export_plan_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyOrganizationClosureExportPlanRepository:
    return SqlAlchemyOrganizationClosureExportPlanRepository(db)


def get_credential_disposition_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyOrganizationClosureCredentialDispositionRepository:
    return SqlAlchemyOrganizationClosureCredentialDispositionRepository(db)


def get_email_account_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyEmailAccountRepository:
    return SqlAlchemyEmailAccountRepository(db)


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


def get_export_planner(
    repository: SqlAlchemyOrganizationClosureExportPlanRepository = Depends(
        get_export_plan_repository
    ),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    lifecycle: OrganizationLifecycleGuard = Depends(get_lifecycle_guard),
    audit: AuditPort = Depends(get_audit_adapter),
) -> OrganizationClosureExportPlanner:
    return OrganizationClosureExportPlanner(repository, authorization, lifecycle, audit)


def get_credential_disposition_service(
    disposition_repository: SqlAlchemyOrganizationClosureCredentialDispositionRepository = Depends(
        get_credential_disposition_repository
    ),
    closure_repository: SqlAlchemyOrganizationClosureRepository = Depends(
        get_closure_repository
    ),
    email_accounts: SqlAlchemyEmailAccountRepository = Depends(
        get_email_account_repository
    ),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    lifecycle: OrganizationLifecycleGuard = Depends(get_lifecycle_guard),
    audit: AuditPort = Depends(get_audit_adapter),
) -> OrganizationClosureCredentialDispositionService:
    return OrganizationClosureCredentialDispositionService(
        disposition_repository,
        closure_repository,
        email_accounts,
        authorization,
        lifecycle,
        audit,
    )


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
    if isinstance(
        exc,
        (
            ClosureAuthorizationUnavailableError,
            ClosureLifecycleUnavailableError,
            ClosureExportPlanningError,
        ),
    ):
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


@router.post(
    "/organizations/{organization_id}/closure-executions/{execution_id}/export-plan",
    response_model=OrganizationClosureExportPlanResponse,
)
def plan_closure_export(
    organization_id: UUID,
    execution_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    planner: OrganizationClosureExportPlanner = Depends(get_export_planner),
) -> OrganizationClosureExportPlanResponse:
    _assert_target_context(auth, organization_id)
    try:
        plan = planner.plan(
            organization_id=organization_id,
            execution_id=execution_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return OrganizationClosureExportPlanResponse.model_validate(plan)


@router.get(
    "/organizations/{organization_id}/closure-executions/{execution_id}/export-plan",
    response_model=OrganizationClosureExportPlanResponse,
)
def get_closure_export_plan(
    organization_id: UUID,
    execution_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    planner: OrganizationClosureExportPlanner = Depends(get_export_planner),
) -> OrganizationClosureExportPlanResponse:
    _assert_target_context(auth, organization_id)
    try:
        plan = planner.get(
            organization_id=organization_id,
            execution_id=execution_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return OrganizationClosureExportPlanResponse.model_validate(plan)


@router.post(
    "/organizations/{organization_id}/closure-executions/{execution_id}/credential-dispositions",
    response_model=OrganizationClosureCredentialDispositionListResponse,
)
def start_credential_dispositions(
    organization_id: UUID,
    execution_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: OrganizationClosureCredentialDispositionService = Depends(
        get_credential_disposition_service
    ),
) -> OrganizationClosureCredentialDispositionListResponse:
    _assert_target_context(auth, organization_id)
    try:
        items = service.start(
            organization_id=organization_id,
            execution_id=execution_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return OrganizationClosureCredentialDispositionListResponse(
        items=[
            OrganizationClosureCredentialDispositionResponse.model_validate(item)
            for item in items
        ]
    )


@router.get(
    "/organizations/{organization_id}/closure-executions/{execution_id}/credential-dispositions",
    response_model=OrganizationClosureCredentialDispositionListResponse,
)
def list_credential_dispositions(
    organization_id: UUID,
    execution_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: OrganizationClosureCredentialDispositionService = Depends(
        get_credential_disposition_service
    ),
) -> OrganizationClosureCredentialDispositionListResponse:
    _assert_target_context(auth, organization_id)
    try:
        items = service.list(
            organization_id=organization_id,
            execution_id=execution_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return OrganizationClosureCredentialDispositionListResponse(
        items=[
            OrganizationClosureCredentialDispositionResponse.model_validate(item)
            for item in items
        ]
    )


@router.get(
    "/organizations/{organization_id}/closure-executions/{execution_id}/credential-dispositions/{disposition_id}",
    response_model=OrganizationClosureCredentialDispositionResponse,
)
def get_credential_disposition(
    organization_id: UUID,
    execution_id: UUID,
    disposition_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: OrganizationClosureCredentialDispositionService = Depends(
        get_credential_disposition_service
    ),
) -> OrganizationClosureCredentialDispositionResponse:
    _assert_target_context(auth, organization_id)
    try:
        item = service.get(
            organization_id=organization_id,
            execution_id=execution_id,
            disposition_id=disposition_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return OrganizationClosureCredentialDispositionResponse.model_validate(item)


@router.post(
    "/organizations/{organization_id}/closure-executions/{execution_id}/credential-dispositions/{disposition_id}/retry",
    response_model=OrganizationClosureCredentialDispositionResponse,
)
def retry_credential_disposition(
    organization_id: UUID,
    execution_id: UUID,
    disposition_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: OrganizationClosureCredentialDispositionService = Depends(
        get_credential_disposition_service
    ),
) -> OrganizationClosureCredentialDispositionResponse:
    _assert_target_context(auth, organization_id)
    try:
        item = service.retry(
            organization_id=organization_id,
            execution_id=execution_id,
            disposition_id=disposition_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return OrganizationClosureCredentialDispositionResponse.model_validate(item)


@router.post(
    "/organizations/{organization_id}/closure-executions/{execution_id}/credential-dispositions/{disposition_id}/reconcile",
    response_model=OrganizationClosureCredentialDispositionResponse,
)
def reconcile_credential_disposition(
    organization_id: UUID,
    execution_id: UUID,
    disposition_id: UUID,
    body: OrganizationClosureCredentialReconcileRequest,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: OrganizationClosureCredentialDispositionService = Depends(
        get_credential_disposition_service
    ),
) -> OrganizationClosureCredentialDispositionResponse:
    _assert_target_context(auth, organization_id)
    try:
        item = service.reconcile(
            organization_id=organization_id,
            execution_id=execution_id,
            disposition_id=disposition_id,
            action=body.action,
            external_credential_id=body.external_credential_id,
            evidence_code=body.evidence_code,
            evidence_reference=body.evidence_reference,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return OrganizationClosureCredentialDispositionResponse.model_validate(item)

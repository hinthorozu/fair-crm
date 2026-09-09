from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
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
    OrganizationClosureArtifactInventoryListResponse,
    OrganizationClosureArtifactInventoryResponse,
    OrganizationClosurePackageResponse,
)
from app.modules.organization_closure.application.closure_package import (
    OrganizationClosurePackageService,
)
from app.modules.organization_closure.application.service import OrganizationClosureError
from app.modules.organization_closure.infrastructure.package_repository import (
    SqlAlchemyOrganizationClosurePackageRepository,
)
from app.modules.system_admin.api.dependencies import (
    bearer_scheme,
    get_audit_adapter,
    get_authorization_adapter,
)

router = APIRouter(prefix="/system-admin", tags=["system-admin"])


def get_closure_package_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyOrganizationClosurePackageRepository:
    return SqlAlchemyOrganizationClosurePackageRepository(db)


def get_closure_package_service(
    repository: SqlAlchemyOrganizationClosurePackageRepository = Depends(
        get_closure_package_repository
    ),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    lifecycle: OrganizationLifecycleGuard = Depends(get_lifecycle_guard),
    audit: AuditPort = Depends(get_audit_adapter),
) -> OrganizationClosurePackageService:
    return OrganizationClosurePackageService(
        repository,
        authorization,
        lifecycle,
        audit,
    )


@router.post(
    "/organizations/{organization_id}/closure-executions/{execution_id}/closure-package",
    response_model=OrganizationClosurePackageResponse,
)
def generate_closure_package(
    organization_id: UUID,
    execution_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: OrganizationClosurePackageService = Depends(get_closure_package_service),
) -> OrganizationClosurePackageResponse:
    _assert_target_context(auth, organization_id)
    try:
        package = service.generate(
            organization_id=organization_id,
            execution_id=execution_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return OrganizationClosurePackageResponse.model_validate(package)


@router.get(
    "/organizations/{organization_id}/closure-executions/{execution_id}/closure-package",
    response_model=OrganizationClosurePackageResponse,
)
def get_closure_package(
    organization_id: UUID,
    execution_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: OrganizationClosurePackageService = Depends(get_closure_package_service),
) -> OrganizationClosurePackageResponse:
    _assert_target_context(auth, organization_id)
    try:
        package = service.get(
            organization_id=organization_id,
            execution_id=execution_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return OrganizationClosurePackageResponse.model_validate(package)


@router.get(
    "/organizations/{organization_id}/closure-executions/{execution_id}/closure-package/artifacts",
    response_model=OrganizationClosureArtifactInventoryListResponse,
)
def list_closure_package_artifacts(
    organization_id: UUID,
    execution_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: OrganizationClosurePackageService = Depends(get_closure_package_service),
    repository: SqlAlchemyOrganizationClosurePackageRepository = Depends(
        get_closure_package_repository
    ),
) -> OrganizationClosureArtifactInventoryListResponse:
    _assert_target_context(auth, organization_id)
    try:
        package = service.get(
            organization_id=organization_id,
            execution_id=execution_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    items = repository.list_inventory(organization_id, execution_id, package.id)
    return OrganizationClosureArtifactInventoryListResponse(
        items=[
            OrganizationClosureArtifactInventoryResponse.model_validate(item)
            for item in items
        ]
    )


@router.get(
    "/organizations/{organization_id}/closure-executions/{execution_id}/closure-package/download",
    response_class=FileResponse,
)
def download_closure_package(
    organization_id: UUID,
    execution_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: OrganizationClosurePackageService = Depends(get_closure_package_service),
) -> FileResponse:
    _assert_target_context(auth, organization_id)
    try:
        package, path = service.resolve_download(
            organization_id=organization_id,
            execution_id=execution_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return FileResponse(
        path,
        media_type="application/zip",
        filename=f"closure-package-{package.id}.zip",
    )

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.super_admin import SuperAdminReader, get_super_admin_reader
from app.modules.fairs.api.dependencies import (
    get_auth_context,
    get_system_fair_duplicate_service,
)

bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
from app.modules.fairs.api.schemas import (
    SystemFairDuplicateListResponse,
    SystemFairKeepSeparateRequest,
    SystemFairMergePreviewRequest,
    SystemFairMergePreviewResponse,
    SystemFairMergeRequest,
)
from app.modules.fairs.application.merge_system_fair import (
    MergeAnalysis,
    SystemFairDuplicateService,
    SystemFairMergeCommand,
)
from app.modules.fairs.domain.exceptions import (
    FairNotFoundError,
    SystemFairAlreadyMergedError,
    SystemFairMergeBlockedError,
)

router = APIRouter(prefix="/fairs", tags=["fairs"])


def _require_system_catalog(
    credentials: HTTPAuthorizationCredentials,
    auth: AuthContext,
    is_super_admin: SuperAdminReader,
) -> None:
    if not is_super_admin(_access_token(credentials), auth.organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System fair catalog changes are restricted",
        )


def _preview_response(analysis: MergeAnalysis) -> SystemFairMergePreviewResponse:
    return SystemFairMergePreviewResponse(
        participations=analysis.participations,
        todos=analysis.todos,
        quotes=analysis.quotes,
        activities=analysis.activities,
        imports=analysis.imports,
        scraper_runs=analysis.scraper_runs,
        email_batches=analysis.email_batches,
        mail_operations=analysis.mail_operations,
        operations=analysis.operations,
        blocking_conflicts=[
            {"code": block.code, "message": block.message} for block in analysis.blocking_conflicts
        ],
    )


def _raise_merge_http(exc: Exception) -> None:
    if isinstance(exc, ForbiddenError):
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if isinstance(exc, FairNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, SystemFairAlreadyMergedError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, SystemFairMergeBlockedError):
        raise HTTPException(
            status_code=409,
            detail="; ".join(item["message"] for item in exc.conflicts),
        ) from exc
    raise exc


@router.get("/system/duplicates", response_model=SystemFairDuplicateListResponse)
def list_system_fair_duplicates(
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    is_super_admin: SuperAdminReader = Depends(get_super_admin_reader),
    service: SystemFairDuplicateService = Depends(get_system_fair_duplicate_service),
) -> SystemFairDuplicateListResponse:
    _require_system_catalog(credentials, auth, is_super_admin)
    groups = service.list_groups()
    return SystemFairDuplicateListResponse(
        items=[
            {
                "identity_name": group.identity_name,
                "city": group.city,
                "fairs": [fair.__dict__ for fair in group.fairs],
            }
            for group in groups
        ]
    )


@router.post("/system/duplicates/preview", response_model=SystemFairMergePreviewResponse)
def preview_system_fair_merge(
    body: SystemFairMergePreviewRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    is_super_admin: SuperAdminReader = Depends(get_super_admin_reader),
    service: SystemFairDuplicateService = Depends(get_system_fair_duplicate_service),
) -> SystemFairMergePreviewResponse:
    _require_system_catalog(credentials, auth, is_super_admin)
    try:
        return _preview_response(service.preview(body.source_fair_id, body.target_fair_id))
    except (ForbiddenError, FairNotFoundError, SystemFairAlreadyMergedError, SystemFairMergeBlockedError) as exc:
        _raise_merge_http(exc)
        raise


@router.post("/system/duplicates/keep-separate")
def keep_system_fairs_separate(
    body: SystemFairKeepSeparateRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    is_super_admin: SuperAdminReader = Depends(get_super_admin_reader),
    service: SystemFairDuplicateService = Depends(get_system_fair_duplicate_service),
) -> dict[str, int]:
    _require_system_catalog(credentials, auth, is_super_admin)
    try:
        created = service.keep_separate(body.fair_ids)
    except (ForbiddenError, FairNotFoundError, SystemFairMergeBlockedError) as exc:
        _raise_merge_http(exc)
        raise
    return {"separated": created}


@router.post("/system/{fair_id}/merge", response_model=SystemFairMergePreviewResponse)
def merge_system_fair(
    fair_id: UUID,
    body: SystemFairMergeRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    is_super_admin: SuperAdminReader = Depends(get_super_admin_reader),
    service: SystemFairDuplicateService = Depends(get_system_fair_duplicate_service),
) -> SystemFairMergePreviewResponse:
    _require_system_catalog(credentials, auth, is_super_admin)
    try:
        analysis = service.merge(
            SystemFairMergeCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                source_fair_id=fair_id,
                target_fair_id=body.target_fair_id,
            )
        )
    except (
        ForbiddenError,
        FairNotFoundError,
        SystemFairAlreadyMergedError,
        SystemFairMergeBlockedError,
    ) as exc:
        _raise_merge_http(exc)
        raise
    return _preview_response(analysis)

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AliasChoices

from app.api.dependencies.list_query import parse_list_query
from app.api.schemas.list_response import StandardListResponse, build_list_response
from app.core.exceptions import ForbiddenError
from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.system_admin.api.dependencies import (
    access_token,
    get_backup_job_runner,
    get_create_backup_use_case,
    get_download_backup_use_case,
    get_get_backup_use_case,
    get_list_backups_use_case,
    get_restore_service,
    require_admin_create_permission,
    require_admin_download_permission,
    require_admin_read_permission,
)
from app.modules.system_admin.api.schemas import (
    CreateSystemBackupRequest,
    CreateSystemBackupResponse,
    ErrorResponse,
    RestoreDisabledResponse,
    SystemBackupResponse,
)
from app.modules.system_admin.application.backup_job_runner import BackupJobCommand
from app.shared.background_jobs import run_blocking_background_task
from app.modules.system_admin.application.backup_service import (
    BACKUP_ALLOWED_SORT_FIELDS,
    BACKUP_DEFAULT_SORT_DIRECTION,
    BACKUP_DEFAULT_SORT_FIELD,
    CreateSystemBackupCommand,
    media_type_for_backup_file,
)
from app.shared.database_backup.formats import BackupFormat
from sqlalchemy.orm import Session

router = APIRouter(prefix="/admin", tags=["Admin — System"])
bearer_scheme = HTTPBearer(auto_error=False)


def _to_response(item) -> SystemBackupResponse:
    return SystemBackupResponse.model_validate(item.__dict__)


@router.post(
    "/backups",
    response_model=CreateSystemBackupResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={403: {"model": ErrorResponse}},
    summary="Create database backup (background job)",
)
def create_system_backup(
    body: CreateSystemBackupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_admin_create_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_create_backup_use_case),
    job_runner=Depends(get_backup_job_runner),
) -> CreateSystemBackupResponse:
    try:
        result = use_case.execute(
            CreateSystemBackupCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                user_email=auth.email,
                access_token=access_token(credentials),
                notes=body.notes,
                backup_format=BackupFormat(body.backup_format),
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    db.commit()
    background_tasks.add_task(
        run_blocking_background_task,
        job_runner.run_backup,
        BackupJobCommand(organization_id=auth.organization_id, backup_id=result.backup_id),
    )
    return CreateSystemBackupResponse(
        id=result.backup_id,
        file_name=result.file_name,
        backup_format=result.backup_format,
        status=result.status,
        progress_stage=result.progress_stage,
    )


@router.get(
    "/backups",
    response_model=StandardListResponse[SystemBackupResponse],
    responses={403: {"model": ErrorResponse}},
    summary="List database backups",
)
def list_system_backups(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 20,
    sort: Annotated[str | None, Query(validation_alias=AliasChoices("sort_by", "sort"))] = None,
    sort_by: Annotated[str | None, Query(include_in_schema=False)] = None,
    sort_order: Annotated[
        str | None,
        Query(pattern="^(?i)(asc|desc)$"),
    ] = None,
    direction: Annotated[
        str | None,
        Query(
            pattern="^(?i)(asc|desc)$",
            validation_alias=AliasChoices("sort_dir", "direction"),
        ),
    ] = None,
    sort_dir: Annotated[str | None, Query(include_in_schema=False)] = None,
    auth: AuthContext = Depends(require_admin_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_list_backups_use_case),
) -> StandardListResponse[SystemBackupResponse]:
    list_query = parse_list_query(
        page=page,
        page_size=page_size,
        sort=sort,
        sort_by=sort_by,
        direction=direction,
        sort_dir=sort_dir,
        sort_order=sort_order or request.query_params.get("sort_order"),
        default_sort=BACKUP_DEFAULT_SORT_FIELD,
        allowed_sort_fields=BACKUP_ALLOWED_SORT_FIELDS,
        default_direction=BACKUP_DEFAULT_SORT_DIRECTION,
    )
    try:
        items, total, resolved_sort, resolved_dir = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=access_token(credentials),
            page=list_query.page,
            page_size=list_query.page_size,
            sort_by=list_query.sort_by,
            sort_dir=list_query.sort_dir,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return build_list_response(
        [_to_response(item) for item in items],
        page=list_query.page,
        page_size=list_query.page_size,
        total=total,
        sort_field=resolved_sort,
        sort_direction=resolved_dir,
    )


@router.get(
    "/backups/{backup_id}",
    response_model=SystemBackupResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Get database backup details",
)
def get_system_backup(
    backup_id: UUID,
    auth: AuthContext = Depends(require_admin_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_get_backup_use_case),
) -> SystemBackupResponse:
    try:
        result = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=access_token(credentials),
            backup_id=backup_id,
            permission_code="fair_crm.admin.backups.read",
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_response(result)


@router.get(
    "/backups/{backup_id}/download",
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Download database backup file",
)
def download_system_backup(
    backup_id: UUID,
    auth: AuthContext = Depends(require_admin_download_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_download_backup_use_case),
):
    try:
        backup, path = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=access_token(credentials),
            backup_id=backup_id,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return FileResponse(
        path=path,
        media_type=media_type_for_backup_file(backup.file_name),
        filename=backup.file_name,
    )


@router.post(
    "/backups/{backup_id}/restore",
    response_model=RestoreDisabledResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Restore database backup (disabled)",
)
def restore_system_backup(
    backup_id: UUID,
    auth: AuthContext = Depends(require_admin_read_permission),
    restore_service=Depends(get_restore_service),
) -> RestoreDisabledResponse:
    _ = (backup_id, auth)
    return RestoreDisabledResponse(
        detail=restore_service.FEATURE_DISABLED_MESSAGE,
        enabled=restore_service.enabled,
    )

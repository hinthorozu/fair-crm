from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
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
    get_delete_backup_use_case,
    get_download_backup_use_case,
    get_get_backup_use_case,
    get_list_backups_use_case,
    get_list_restore_jobs_use_case,
    get_get_restore_job_use_case,
    get_get_restore_job_log_use_case,
    get_restore_backup_from_upload_use_case,
    get_restore_backup_use_case,
    require_admin_create_permission,
    require_admin_download_permission,
    require_admin_read_permission,
)
from app.modules.system_admin.api.schemas import (
    CreateSystemBackupBatchResponse,
    CreateSystemBackupRequest,
    CreateSystemBackupResponse,
    DeleteSystemBackupResponse,
    ErrorResponse,
    RestoreJobLogResponse,
    SystemBackupRestoreJobResponse,
    SystemBackupResponse,
)
from app.modules.system_admin.application.backup_job_runner import BackupJobCommand
from app.shared.background_jobs import run_blocking_background_task
from app.modules.system_admin.application.backup_service import (
    BACKUP_ALLOWED_SORT_FIELDS,
    BACKUP_DEFAULT_SORT_DIRECTION,
    BACKUP_DEFAULT_SORT_FIELD,
    CreateSystemBackupCommand,
    DeleteSystemBackupCommand,
    RestoreSystemBackupCommand,
    RestoreSystemBackupFromUploadCommand,
    media_type_for_backup_file,
)
from app.shared.database_backup.database_keys import DatabaseKey, parse_database_keys
from app.modules.system_admin.application.restore_job_service import (
    RESTORE_JOB_ALLOWED_SORT_FIELDS,
    RESTORE_JOB_DEFAULT_SORT_DIRECTION,
    RESTORE_JOB_DEFAULT_SORT_FIELD,
)
from app.shared.database_backup.formats import BackupFormat
from sqlalchemy.orm import Session

router = APIRouter(prefix="/admin", tags=["Admin — System"])
bearer_scheme = HTTPBearer(auto_error=False)


def _to_response(item) -> SystemBackupResponse:
    return SystemBackupResponse.model_validate(item.__dict__)


def _to_restore_job_response(item) -> SystemBackupRestoreJobResponse:
    return SystemBackupRestoreJobResponse.model_validate(item.__dict__)


@router.post(
    "/backups",
    response_model=CreateSystemBackupBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={403: {"model": ErrorResponse}},
    summary="Create database backup jobs for one or more platform databases",
)
def create_system_backup(
    body: CreateSystemBackupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_admin_create_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_create_backup_use_case),
    job_runner=Depends(get_backup_job_runner),
) -> CreateSystemBackupBatchResponse:
    try:
        database_keys = parse_database_keys(body.database_keys)
        batch = use_case.execute(
            CreateSystemBackupCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                user_email=auth.email,
                access_token=access_token(credentials),
                notes=body.notes,
                backup_format=BackupFormat(body.backup_format),
                database_keys=database_keys,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.commit()
    for item in batch.items:
        background_tasks.add_task(
            run_blocking_background_task,
            job_runner.run_backup,
            BackupJobCommand(organization_id=auth.organization_id, backup_id=item.backup_id),
        )
    return CreateSystemBackupBatchResponse(
        items=[
            CreateSystemBackupResponse(
                id=item.backup_id,
                database_key=item.database_key,
                database_label=item.database_label,
                file_name=item.file_name,
                backup_format=item.backup_format,
                status=item.status,
                progress_stage=item.progress_stage,
            )
            for item in batch.items
        ]
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
    "/backups/restore-jobs",
    response_model=StandardListResponse[SystemBackupRestoreJobResponse],
    responses={403: {"model": ErrorResponse}},
    summary="List database restore jobs",
)
def list_restore_jobs(
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
    use_case=Depends(get_list_restore_jobs_use_case),
) -> StandardListResponse[SystemBackupRestoreJobResponse]:
    list_query = parse_list_query(
        page=page,
        page_size=page_size,
        sort=sort,
        sort_by=sort_by,
        direction=direction,
        sort_dir=sort_dir,
        sort_order=sort_order or request.query_params.get("sort_order"),
        default_sort=RESTORE_JOB_DEFAULT_SORT_FIELD,
        allowed_sort_fields=RESTORE_JOB_ALLOWED_SORT_FIELDS,
        default_direction=RESTORE_JOB_DEFAULT_SORT_DIRECTION,
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
        [_to_restore_job_response(item) for item in items],
        page=list_query.page,
        page_size=list_query.page_size,
        total=total,
        sort_field=resolved_sort,
        sort_direction=resolved_dir,
    )


@router.get(
    "/backups/restore-jobs/{job_id}",
    response_model=SystemBackupRestoreJobResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Get database restore job details",
)
def get_restore_job(
    job_id: UUID,
    auth: AuthContext = Depends(require_admin_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_get_restore_job_use_case),
) -> SystemBackupRestoreJobResponse:
    try:
        result = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=access_token(credentials),
            job_id=job_id,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_restore_job_response(result)


@router.get(
    "/backups/restore-jobs/{job_id}/log",
    response_model=RestoreJobLogResponse,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
    summary="Get restore job log content",
)
def get_restore_job_log(
    job_id: UUID,
    auth: AuthContext = Depends(require_admin_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_get_restore_job_log_use_case),
) -> RestoreJobLogResponse:
    try:
        result = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=access_token(credentials),
            job_id=job_id,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return RestoreJobLogResponse.model_validate(result.__dict__)


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
    "/backups/restore/upload",
    response_model=SystemBackupRestoreJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={403: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Restore database from uploaded .dump file (job record)",
)
async def restore_system_backup_from_upload(
    file: UploadFile = File(...),
    notes: str | None = Form(default=None),
    database_key: str = Form(default=DatabaseKey.FAIR_CRM.value),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_admin_create_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_restore_backup_from_upload_use_case),
) -> SystemBackupRestoreJobResponse:
    original_name = file.filename or ""
    payload = await file.read()
    try:
        parsed_database_key = DatabaseKey(database_key)
        result = use_case.execute(
            RestoreSystemBackupFromUploadCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                user_email=auth.email,
                access_token=access_token(credentials),
                original_file_name=original_name,
                file_bytes=payload,
                notes=notes.strip() if notes else None,
                database_key=parsed_database_key,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return _to_restore_job_response(result)


@router.post(
    "/backups/{backup_id}/restore",
    response_model=SystemBackupRestoreJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
    summary="Restore database backup (job record; manual restore required)",
)
def restore_system_backup(
    backup_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_admin_create_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_restore_backup_use_case),
) -> SystemBackupRestoreJobResponse:
    try:
        result = use_case.execute(
            RestoreSystemBackupCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                user_email=auth.email,
                access_token=access_token(credentials),
                backup_id=backup_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return _to_restore_job_response(result)


@router.delete(
    "/backups/{backup_id}",
    response_model=DeleteSystemBackupResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Delete database backup record and file",
)
def delete_system_backup(
    backup_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_admin_create_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_delete_backup_use_case),
) -> DeleteSystemBackupResponse:
    try:
        result = use_case.execute(
            DeleteSystemBackupCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=access_token(credentials),
                backup_id=backup_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    db.commit()
    return DeleteSystemBackupResponse.model_validate(result.__dict__)

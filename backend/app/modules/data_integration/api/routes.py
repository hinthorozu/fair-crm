from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AliasChoices
from sqlalchemy.orm import Session

from app.api.dependencies.list_query import parse_list_query
from app.api.schemas.list_response import StandardListResponse, build_list_response
from app.core.exceptions import ForbiddenError
from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.data_integration.api.dependencies import (
    get_get_import_job_use_case,
    get_job_runner,
    get_list_import_batches_use_case,
    get_select_import_sheet_use_case,
    get_start_import_analyze_job_use_case,
    get_start_import_apply_job_use_case,
    require_read_permission,
)
from app.modules.data_integration.api.schemas import (
    ErrorResponse,
    ImportBatchResponse,
    ImportJobResponse,
    SelectImportSheetRequest,
    SelectImportSheetResponse,
    StartImportJobResponse,
)
from app.modules.data_integration.application.list_import_batches import (
    ALLOWED_SORT_FIELDS as IMPORT_BATCH_ALLOWED_SORT_FIELDS,
    DEFAULT_SORT_DIRECTION as IMPORT_BATCH_DEFAULT_SORT_DIRECTION,
    DEFAULT_SORT_FIELD as IMPORT_BATCH_DEFAULT_SORT_FIELD,
)
from app.modules.data_integration.application.get_import_job import GetImportJobQuery
from app.modules.data_integration.application.select_import_sheet import SelectImportSheetUseCase
from app.modules.data_integration.application.start_import_apply_job import (
    StartImportApplyJobCommand,
    StartImportApplyJobUseCase,
)
from app.modules.imports.api.routes import _access_token, _batch_response, bearer_scheme
from app.modules.imports.application.commands import ListImportBatchesQuery, SelectImportSheetCommand
from app.modules.data_integration.application.start_import_analyze_job import (
    StartImportAnalyzeJobCommand,
    StartImportAnalyzeJobUseCase,
)
from app.modules.imports.domain.exceptions import (
    ImportApplyInProgressError,
    ImportAnalyzeInProgressError,
    ImportBatchAlreadyAppliedError,
    ImportBatchAnalyzeNotAllowedError,
    ImportBatchNotFoundError,
    ImportBulkActionInProgressError,
    InvalidImportFileError,
)

router = APIRouter(prefix="/data-integration", tags=["data-integration"])


@router.get(
    "/imports",
    response_model=StandardListResponse[ImportBatchResponse],
    summary="List import batches (Data Integration workspace)",
)
def list_import_batches(
    page: int = Query(default=1, ge=1),
    page_size: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 25,
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
    auth: AuthContext = Depends(require_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_list_import_batches_use_case),
) -> StandardListResponse[ImportBatchResponse]:
    list_query = parse_list_query(
        page=page,
        page_size=page_size,
        sort=sort,
        sort_by=sort_by,
        direction=direction,
        sort_dir=sort_dir,
        sort_order=sort_order,
        default_sort=IMPORT_BATCH_DEFAULT_SORT_FIELD,
        allowed_sort_fields=IMPORT_BATCH_ALLOWED_SORT_FIELDS,
        default_direction=IMPORT_BATCH_DEFAULT_SORT_DIRECTION,
    )
    result = use_case.execute(
        ListImportBatchesQuery(
            organization_id=auth.organization_id,
            page=list_query.page,
            page_size=list_query.page_size,
            sort_by=list_query.sort_by,
            sort_dir=list_query.sort_dir,
        ),
    )
    return build_list_response(
        [ImportBatchResponse.model_validate(item.__dict__) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        sort_field=list_query.sort_by,
        sort_direction=list_query.sort_dir,
    )


@router.patch(
    "/imports/{batch_id}/sheet",
    response_model=SelectImportSheetResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Select Excel worksheet for import batch",
)
def select_import_sheet(
    batch_id: UUID,
    body: SelectImportSheetRequest,
    auth: AuthContext = Depends(require_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: SelectImportSheetUseCase = Depends(get_select_import_sheet_use_case),
) -> SelectImportSheetResponse:
    try:
        result = use_case.execute(
            SelectImportSheetCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                batch_id=batch_id,
                sheet_name=body.sheet_name,
                file_content=b"",
            )
        )
    except ImportBatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidImportFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return SelectImportSheetResponse.model_validate(result.__dict__)


@router.post(
    "/imports/{batch_id}/analyze-job",
    response_model=StartImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Start background import analyze job",
)
def start_import_analyze_job(
    batch_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: StartImportAnalyzeJobUseCase = Depends(get_start_import_analyze_job_use_case),
    job_runner=Depends(get_job_runner),
) -> StartImportJobResponse:
    try:
        result = use_case.execute(
            StartImportAnalyzeJobCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                batch_id=batch_id,
            )
        )
    except ImportBatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ImportBatchAnalyzeNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ImportAnalyzeInProgressError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    db.commit()
    background_tasks.add_task(job_runner.run_analyze, result.analyze_command)
    return StartImportJobResponse(
        job_id=result.job_id,
        batch_id=result.batch_id,
        status=result.status,
        progress_total=result.progress_total,
    )


@router.post(
    "/imports/{batch_id}/apply-job",
    response_model=StartImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Start background import apply job",
)
def start_import_apply_job(
    batch_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: StartImportApplyJobUseCase = Depends(get_start_import_apply_job_use_case),
    job_runner=Depends(get_job_runner),
) -> StartImportJobResponse:
    try:
        result = use_case.execute(
            StartImportApplyJobCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                batch_id=batch_id,
            )
        )
    except ImportBatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ImportBatchAlreadyAppliedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (ImportApplyInProgressError, ImportBulkActionInProgressError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    db.commit()
    background_tasks.add_task(job_runner.run_apply, result.apply_command)
    return StartImportJobResponse(
        job_id=result.job_id,
        batch_id=result.batch_id,
        status=result.status,
        progress_total=result.progress_total,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=ImportJobResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get import background job status",
)
def get_import_job(
    job_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_get_import_job_use_case),
) -> ImportJobResponse:
    try:
        result = use_case.execute(
            GetImportJobQuery(organization_id=auth.organization_id, job_id=job_id),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ImportJobResponse.model_validate(result.__dict__)

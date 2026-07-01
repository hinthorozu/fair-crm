from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AliasChoices

from app.api.dependencies.list_query import parse_list_query, resolve_page_size_from_request
from app.api.list_helpers import standard_list_from_result
from app.modules.imports.application.list_import_rows import (
    ALLOWED_SORT_FIELDS,
    DEFAULT_SORT_DIRECTION,
    DEFAULT_SORT_FIELD,
)

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.imports.api.dependencies import (
    get_analyze_import_use_case,
    get_apply_import_use_case,
    get_auth_context,
    get_bulk_row_decision_use_case,
    get_get_import_batch_use_case,
    get_list_import_rows_use_case,
    get_set_column_mapping_use_case,
    get_set_row_decision_use_case,
    get_upload_import_use_case,
    get_upload_raw_import_use_case,
    require_read_permission,
)
from app.modules.imports.api.schemas import (
    AnalyzeImportResponse,
    ApplyImportResponse,
    BulkRowDecisionRequest,
    BulkRowDecisionResponse,
    ErrorResponse,
    ImportBatchResponse,
    ImportRowListResponse,
    ImportRowResponse,
    SetColumnMappingRequest,
    SetColumnMappingResponse,
    SetImportRowDecisionRequest,
    UploadRawImportResponse,
)
from app.modules.imports.application.analyze_import import AnalyzeImportUseCase
from app.modules.imports.application.apply_import import ApplyImportUseCase
from app.modules.imports.application.bulk_row_decision import BulkRowDecisionUseCase
from app.modules.imports.application.commands import (
    AnalyzeImportCommand,
    ApplyImportCommand,
    BulkRowDecisionCommand,
    GetImportBatchQuery,
    ListImportRowsQuery,
    SetColumnMappingCommand,
    SetImportRowDecisionCommand,
    UploadImportCommand,
    UploadRawImportCommand,
)
from app.modules.imports.application.get_import_batch import GetImportBatchUseCase
from app.modules.imports.application.list_import_rows import ListImportRowsUseCase
from app.modules.imports.application.set_column_mapping import SetColumnMappingUseCase
from app.modules.imports.application.set_row_decision import SetImportRowDecisionUseCase
from app.modules.imports.application.upload_import import UploadCustomerImportUseCase
from app.modules.imports.application.upload_raw_import import UploadRawImportUseCase
from app.modules.imports.domain.exceptions import (
    FairRequiredError,
    ImportBatchAlreadyAppliedError,
    ImportBatchNotFoundError,
    ImportRowNotFoundError,
    InvalidColumnMappingError,
    InvalidImportDecisionError,
    InvalidImportFileError,
)

router = APIRouter(prefix="/imports", tags=["imports"])
bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _batch_response(result) -> ImportBatchResponse:
    return ImportBatchResponse.model_validate(result.__dict__)


def _row_response(result) -> ImportRowResponse:
    return ImportRowResponse.model_validate(result.__dict__)


@router.post(
    "/upload",
    response_model=UploadRawImportResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Upload Excel for wizard (raw preview, no CRM writes)",
)
async def upload_raw_import(
    fair_id: UUID = Form(...),
    file: UploadFile = File(...),
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: UploadRawImportUseCase = Depends(get_upload_raw_import_use_case),
) -> UploadRawImportResponse:
    file_name = file.filename or "import.xlsx"
    content = await file.read()
    try:
        result = use_case.execute(
            UploadRawImportCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                fair_id=fair_id,
                file_name=file_name,
                file_content=content,
            )
        )
    except InvalidImportFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FairRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FairNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return UploadRawImportResponse.model_validate(result.__dict__)


@router.post(
    "/customers/upload",
    response_model=ImportBatchResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="Upload customer import xlsx (legacy v1 — deprecated, removal planned v0.9.0)",
    deprecated=True,
)
async def upload_customer_import(
    file: UploadFile = File(...),
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: UploadCustomerImportUseCase = Depends(get_upload_import_use_case),
) -> ImportBatchResponse:
    file_name = file.filename or "import.xlsx"
    content = await file.read()
    try:
        result = use_case.execute(
            UploadImportCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                file_name=file_name,
                file_content=content,
            )
        )
    except InvalidImportFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return _batch_response(result)


@router.get(
    "/{batch_id}",
    response_model=ImportBatchResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get import batch summary",
)
def get_import_batch(
    batch_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    use_case: GetImportBatchUseCase = Depends(get_get_import_batch_use_case),
) -> ImportBatchResponse:
    try:
        result = use_case.execute(
            GetImportBatchQuery(organization_id=auth.organization_id, batch_id=batch_id)
        )
    except ImportBatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _batch_response(result)


@router.patch(
    "/{batch_id}/column-mapping",
    response_model=SetColumnMappingResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Set column mapping for import batch",
)
def set_column_mapping(
    batch_id: UUID,
    body: SetColumnMappingRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: SetColumnMappingUseCase = Depends(get_set_column_mapping_use_case),
) -> SetColumnMappingResponse:
    mappings = {key: spec.model_dump() for key, spec in body.mappings.items()}
    try:
        result = use_case.execute(
            SetColumnMappingCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                batch_id=batch_id,
                has_header_row=body.has_header_row,
                mappings=mappings,
            )
        )
    except ImportBatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ImportBatchAlreadyAppliedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InvalidColumnMappingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return SetColumnMappingResponse.model_validate(result.__dict__)


@router.post(
    "/{batch_id}/analyze",
    response_model=AnalyzeImportResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Analyze import batch with current mapping",
)
def analyze_import_batch(
    batch_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: AnalyzeImportUseCase = Depends(get_analyze_import_use_case),
) -> AnalyzeImportResponse:
    try:
        result = use_case.execute(
            AnalyzeImportCommand(
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
    except InvalidColumnMappingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return AnalyzeImportResponse(
        batch=_batch_response(result.batch),
        total_rows=result.total_rows,
    )


@router.get(
    "/{batch_id}/rows",
    response_model=ImportRowListResponse,
    responses={404: {"model": ErrorResponse}},
    summary="List import batch rows",
)
def list_import_rows(
    request: Request,
    batch_id: UUID,
    filter: str | None = Query(
        default=None,
        description="all | new | will_update | duplicate | invalid | skip",
    ),
    search: str | None = Query(default=None, description="Filter by company name"),
    page: int = Query(default=1, ge=1),
    page_size: Annotated[
        int,
        Query(ge=1, le=100, validation_alias=AliasChoices("pageSize", "page_size")),
    ] = 25,
    sort: Annotated[
        str | None,
        Query(validation_alias=AliasChoices("sort", "sort_by")),
    ] = None,
    sort_by: Annotated[str | None, Query(include_in_schema=False)] = None,
    direction: Annotated[
        str | None,
        Query(pattern="^(?i)(asc|desc)$", validation_alias=AliasChoices("direction", "sort_dir")),
    ] = None,
    sort_dir: Annotated[str | None, Query(include_in_schema=False)] = None,
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListImportRowsUseCase = Depends(get_list_import_rows_use_case),
) -> ImportRowListResponse:
    list_query = parse_list_query(
        page=page,
        page_size=resolve_page_size_from_request(request, page_size),
        search=search,
        sort=sort,
        sort_by=sort_by,
        direction=direction,
        sort_dir=sort_dir,
        default_sort=DEFAULT_SORT_FIELD,
        allowed_sort_fields=ALLOWED_SORT_FIELDS,
        default_direction=DEFAULT_SORT_DIRECTION,
    )
    try:
        result = use_case.execute(
            ListImportRowsQuery(
                organization_id=auth.organization_id,
                batch_id=batch_id,
                filter=filter,
                search=list_query.search,
                page=list_query.page,
                page_size=list_query.page_size,
                sort_by=list_query.sort_by,
                sort_dir=list_query.sort_dir,
            )
        )
    except ImportBatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    filters: dict = {}
    if filter:
        filters["filter"] = filter
    if list_query.search:
        filters["search"] = list_query.search

    return standard_list_from_result(
        result,
        sort_field=list_query.sort_by,
        sort_direction=list_query.sort_dir,
        filters=filters,
    ).model_copy(
        update={"items": [_row_response(item) for item in result.items]},
    )


@router.patch(
    "/{batch_id}/rows/{row_id}/decision",
    response_model=ImportRowResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Set import row merge decision",
)
def set_import_row_decision(
    batch_id: UUID,
    row_id: UUID,
    body: SetImportRowDecisionRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: SetImportRowDecisionUseCase = Depends(get_set_row_decision_use_case),
) -> ImportRowResponse:
    try:
        result = use_case.execute(
            SetImportRowDecisionCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                batch_id=batch_id,
                row_id=row_id,
                decision=body.decision,
                match_customer_id=body.match_customer_id,
            )
        )
    except ImportBatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ImportRowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ImportBatchAlreadyAppliedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InvalidImportDecisionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return _row_response(result)


@router.patch(
    "/{batch_id}/rows/bulk-decision",
    response_model=BulkRowDecisionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Bulk set import row decisions",
)
def bulk_row_decision(
    batch_id: UUID,
    body: BulkRowDecisionRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: BulkRowDecisionUseCase = Depends(get_bulk_row_decision_use_case),
) -> BulkRowDecisionResponse:
    try:
        result = use_case.execute(
            BulkRowDecisionCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                batch_id=batch_id,
                action=body.action,
            )
        )
    except ImportBatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ImportBatchAlreadyAppliedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return BulkRowDecisionResponse(updated_count=result.updated_count)


@router.post(
    "/{batch_id}/apply",
    response_model=ApplyImportResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Apply import batch decisions",
)
def apply_import_batch(
    batch_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: ApplyImportUseCase = Depends(get_apply_import_use_case),
) -> ApplyImportResponse:
    try:
        result = use_case.execute(
            ApplyImportCommand(
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
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return ApplyImportResponse(
        batch=_batch_response(result.batch),
        created_rows=result.created_rows,
        updated_rows=result.updated_rows,
        skipped_rows=result.skipped_rows,
        invalid_rows=result.invalid_rows,
        created_participations=result.created_participations,
        updated_participations=result.updated_participations,
        created_contacts=result.created_contacts,
    )

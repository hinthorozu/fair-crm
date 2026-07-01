from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.imports.api.dependencies import (
    get_apply_import_use_case,
    get_auth_context,
    get_get_import_batch_use_case,
    get_list_import_rows_use_case,
    get_set_row_decision_use_case,
    get_upload_import_use_case,
    require_read_permission,
)
from app.modules.imports.api.schemas import (
    ApplyImportResponse,
    ErrorResponse,
    ImportBatchResponse,
    ImportRowListResponse,
    ImportRowResponse,
    SetImportRowDecisionRequest,
)
from app.modules.imports.application.apply_import import ApplyImportUseCase
from app.modules.imports.application.commands import (
    ApplyImportCommand,
    GetImportBatchQuery,
    ListImportRowsQuery,
    SetImportRowDecisionCommand,
    UploadImportCommand,
)
from app.modules.imports.application.get_import_batch import GetImportBatchUseCase
from app.modules.imports.application.list_import_rows import ListImportRowsUseCase
from app.modules.imports.application.set_row_decision import SetImportRowDecisionUseCase
from app.modules.imports.application.upload_import import UploadCustomerImportUseCase
from app.modules.imports.domain.exceptions import (
    ImportBatchAlreadyAppliedError,
    ImportBatchNotFoundError,
    ImportRowNotFoundError,
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
    "/customers/upload",
    response_model=ImportBatchResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="Upload customer import xlsx",
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


@router.get(
    "/{batch_id}/rows",
    response_model=ImportRowListResponse,
    responses={404: {"model": ErrorResponse}},
    summary="List import batch rows",
)
def list_import_rows(
    batch_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListImportRowsUseCase = Depends(get_list_import_rows_use_case),
) -> ImportRowListResponse:
    try:
        result = use_case.execute(
            ListImportRowsQuery(organization_id=auth.organization_id, batch_id=batch_id)
        )
    except ImportBatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ImportRowListResponse(
        items=[_row_response(item) for item in result.items],
        total=result.total,
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
    )

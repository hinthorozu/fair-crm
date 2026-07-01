from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.fairs.api.dependencies import (
    get_archive_fair_use_case,
    get_auth_context,
    get_create_fair_use_case,
    get_get_fair_use_case,
    get_list_fairs_use_case,
    get_restore_fair_use_case,
    get_update_fair_use_case,
    require_read_permission,
)
from app.modules.fairs.api.schemas import (
    CreateFairRequest,
    ErrorResponse,
    FairListResponse,
    FairResponse,
    UpdateFairRequest,
)
from app.modules.fairs.application.archive_fair import ArchiveFairUseCase
from app.modules.fairs.application.commands import (
    ArchiveFairCommand,
    CreateFairCommand,
    GetFairQuery,
    ListFairsQuery,
    RestoreFairCommand,
    UpdateFairCommand,
)
from app.modules.fairs.application.create_fair import CreateFairUseCase
from app.modules.fairs.application.get_fair import GetFairUseCase
from app.modules.fairs.application.list_fairs import ListFairsUseCase
from app.modules.fairs.application.restore_fair import RestoreFairUseCase
from app.modules.fairs.application.update_fair import UpdateFairUseCase
from app.modules.fairs.domain.exceptions import (
    FairAlreadyArchivedError,
    FairNotArchivedError,
    FairNotFoundError,
    InvalidFairDateRangeError,
    InvalidFairNameError,
)
from app.modules.fairs.domain.value_objects import FairStatus

router = APIRouter(prefix="/fairs", tags=["fairs"])
bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _to_response(result) -> FairResponse:
    return FairResponse.model_validate(result.__dict__)


@router.post(
    "",
    response_model=FairResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def create_fair(
    body: CreateFairRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: CreateFairUseCase = Depends(get_create_fair_use_case),
) -> FairResponse:
    try:
        result = use_case.execute(
            CreateFairCommand(
                organization_id=auth.organization_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                **body.model_dump(),
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except InvalidFairNameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidFairDateRangeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.get(
    "",
    response_model=FairListResponse,
    responses={403: {"model": ErrorResponse}},
)
def list_fairs(
    request: Request,
    fair_status: FairStatus | None = Query(default=None, alias="status"),
    include_archived: bool = Query(default=False),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc", pattern="^(?i)(asc|desc)$"),
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListFairsUseCase = Depends(get_list_fairs_use_case),
) -> FairListResponse:
    raw_status = request.query_params.get("status")
    if fair_status == FairStatus.ARCHIVED or raw_status == FairStatus.ARCHIVED.value:
        list_status = FairStatus.ARCHIVED
        list_include_archived = True
    elif include_archived and raw_status is None and fair_status is None:
        list_status = FairStatus.ARCHIVED
        list_include_archived = True
    elif fair_status is not None:
        list_status = fair_status
        list_include_archived = False
    elif raw_status and raw_status != FairStatus.ARCHIVED.value:
        try:
            list_status = FairStatus(raw_status)
            list_include_archived = False
        except ValueError:
            list_status = None
            list_include_archived = False
    else:
        list_status = None
        list_include_archived = False

    result = use_case.execute(
        ListFairsQuery(
            organization_id=auth.organization_id,
            status=list_status,
            include_archived=list_include_archived,
            search=search,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    )
    return FairListResponse(
        items=[_to_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )


@router.post(
    "/{fair_id}/restore",
    response_model=FairResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def restore_fair(
    fair_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: RestoreFairUseCase = Depends(get_restore_fair_use_case),
) -> FairResponse:
    try:
        result = use_case.execute(
            RestoreFairCommand(
                organization_id=auth.organization_id,
                fair_id=fair_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FairNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FairNotArchivedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.get(
    "/{fair_id}",
    response_model=FairResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_fair(
    fair_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    use_case: GetFairUseCase = Depends(get_get_fair_use_case),
) -> FairResponse:
    try:
        result = use_case.execute(
            GetFairQuery(
                organization_id=auth.organization_id,
                fair_id=fair_id,
            )
        )
    except FairNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(result)


@router.patch(
    "/{fair_id}",
    response_model=FairResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def update_fair(
    fair_id: UUID,
    body: UpdateFairRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: UpdateFairUseCase = Depends(get_update_fair_use_case),
) -> FairResponse:
    try:
        result = use_case.execute(
            UpdateFairCommand(
                organization_id=auth.organization_id,
                fair_id=fair_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                **body.model_dump(exclude_unset=True),
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FairNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FairAlreadyArchivedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidFairNameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidFairDateRangeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.delete(
    "/{fair_id}",
    response_model=FairResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def archive_fair(
    fair_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: ArchiveFairUseCase = Depends(get_archive_fair_use_case),
) -> FairResponse:
    try:
        result = use_case.execute(
            ArchiveFairCommand(
                organization_id=auth.organization_id,
                fair_id=fair_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FairNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(result)

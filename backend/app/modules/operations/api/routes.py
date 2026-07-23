from dataclasses import asdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AliasChoices
from sqlalchemy.orm import Session

from app.api.dependencies.list_query import parse_list_query, resolve_page_size_from_request
from app.api.list_helpers import standard_list_from_result
from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.fairs.api.dependencies import get_fair_scraper_job_runner
from app.modules.operations.api.dependencies import (
    ScraperJobBuffer,
    get_auth_context,
    get_cancel_operation_use_case,
    get_create_operation_use_case,
    get_get_operation_use_case,
    get_list_operation_runs_use_case,
    get_list_operation_types_use_case,
    get_list_operations_use_case,
    get_retry_operation_use_case,
    get_scraper_job_buffer,
    get_start_operation_use_case,
    get_update_operation_type_capabilities_use_case,
    get_wizard_metadata_use_case,
    require_read_permission,
)
from app.modules.scraper.application.fair_scraper_job_runner import FairScraperJobRunner
from app.shared.background_jobs import run_blocking_background_task
from app.modules.operations.api.schemas import (
    CreateOperationRequest,
    ErrorResponse,
    OperationDetailResponse,
    OperationListResponse,
    OperationResponse,
    OperationRunListResponse,
    OperationRunResponse,
    OperationTypeCatalogItemResponse,
    OperationTypeCatalogListResponse,
    UpdateOperationTypeCapabilitiesRequest,
    WizardMetadataResponse,
)
from app.modules.operations.application.cancel_operation import CancelOperationUseCase
from app.modules.operations.application.commands import (
    CancelOperationCommand,
    CreateOperationCommand,
    GetOperationQuery,
    ListOperationRunsQuery,
    ListOperationsQuery,
    RetryOperationCommand,
    StartOperationCommand,
)
from app.modules.operations.application.create_operation import CreateOperationUseCase
from app.modules.operations.application.get_operation import GetOperationUseCase
from app.modules.operations.application.get_wizard_metadata import GetWizardMetadataUseCase
from app.modules.operations.application.list_operation_runs import ListOperationRunsUseCase
from app.modules.operations.application.list_operation_types import (
    ListOperationTypesUseCase,
    OperationTypeListItem,
)
from app.modules.operations.application.list_operations import ListOperationsUseCase
from app.modules.operations.application.retry_operation import RetryOperationUseCase
from app.modules.operations.application.start_operation import StartOperationUseCase
from app.modules.operations.application.update_operation_type_capabilities import (
    UpdateOperationTypeCapabilitiesCommand,
    UpdateOperationTypeCapabilitiesUseCase,
)
from app.modules.operations.domain.exceptions import (
    HandlerCapabilityNotSupportedError,
    HandlerNotRegisteredError,
    InvalidOperationConfigError,
    InvalidOperationStatusTransitionError,
    InvalidOperationTitleError,
    InvalidOperationTypeError,
    InvalidRunStatusTransitionError,
    InvalidSourceKindError,
    OperationNotFoundError,
    OperationRunNotFoundError,
)
from app.modules.operations.domain.value_objects import HandlerCapabilities

router = APIRouter(prefix="/operations", tags=["operations"])
bearer_scheme = HTTPBearer(auto_error=False)

ALLOWED_SORT_FIELDS = frozenset(
    {"title", "created_at", "updated_at", "status", "operation_type", "priority"}
)
DEFAULT_SORT_FIELD = "created_at"
DEFAULT_SORT_DIRECTION = "desc"
RUN_ALLOWED_SORT_FIELDS = frozenset(
    {"created_at", "updated_at", "started_at", "finished_at", "status", "attempt"}
)


def _to_operation_type_catalog_item(item: OperationTypeListItem) -> OperationTypeCatalogItemResponse:
    return OperationTypeCatalogItemResponse(
        key=item.key,
        name=item.name,
        is_active=item.is_active,
        sort_order=item.sort_order,
        supports_pause=item.supports_pause,
        supports_resume=item.supports_resume,
        supports_retry=item.supports_retry,
        supports_schedule=item.supports_schedule,
        supports_items=item.supports_items,
        updated_at=item.updated_at,
    )


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _to_operation_response(result) -> OperationResponse:
    payload = asdict(result)
    latest_run = payload.pop("latest_run", None)
    response = OperationResponse.model_validate(payload)
    if latest_run is not None:
        response.latest_run = OperationRunResponse.model_validate(latest_run)
    return response


def _to_run_response(result) -> OperationRunResponse:
    return OperationRunResponse.model_validate(asdict(result))


def _schedule_scraper_jobs(
    *,
    background_tasks: BackgroundTasks,
    scraper_job_buffer: ScraperJobBuffer,
    job_runner: FairScraperJobRunner,
) -> None:
    for command in scraper_job_buffer.drain():
        background_tasks.add_task(
            run_blocking_background_task,
            job_runner.run_fair_scraper,
            command,
        )


def _map_domain_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ForbiddenError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, (OperationNotFoundError, OperationRunNotFoundError)):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(
        exc,
        (
            InvalidOperationConfigError,
            InvalidOperationTitleError,
            InvalidOperationTypeError,
            InvalidSourceKindError,
            InvalidOperationStatusTransitionError,
            InvalidRunStatusTransitionError,
        ),
    ):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(
        exc,
        (
            HandlerNotRegisteredError,
            HandlerCapabilityNotSupportedError,
        ),
    ):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/wizard-metadata",
    response_model=WizardMetadataResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_wizard_metadata(
    _: AuthContext = Depends(require_read_permission),
    use_case: GetWizardMetadataUseCase = Depends(get_wizard_metadata_use_case),
) -> WizardMetadataResponse:
    result = use_case.execute()
    return WizardMetadataResponse.model_validate(asdict(result))


@router.get(
    "/types",
    response_model=OperationTypeCatalogListResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_operation_types(
    _: AuthContext = Depends(require_read_permission),
    active_only: bool = Query(False),
    use_case: ListOperationTypesUseCase = Depends(get_list_operation_types_use_case),
) -> OperationTypeCatalogListResponse:
    result = use_case.execute(active_only=active_only)
    return OperationTypeCatalogListResponse(
        items=[_to_operation_type_catalog_item(item) for item in result.items]
    )


@router.patch(
    "/types/{type_key}/capabilities",
    response_model=OperationTypeCatalogItemResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def update_operation_type_capabilities(
    type_key: str,
    body: UpdateOperationTypeCapabilitiesRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    use_case: UpdateOperationTypeCapabilitiesUseCase = Depends(
        get_update_operation_type_capabilities_use_case
    ),
) -> OperationTypeCatalogItemResponse:
    try:
        item = use_case.execute(
            UpdateOperationTypeCapabilitiesCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                key=type_key,
                capabilities=HandlerCapabilities(
                    supports_pause=body.supports_pause,
                    supports_resume=body.supports_resume,
                    supports_retry=body.supports_retry,
                    supports_schedule=body.supports_schedule,
                    supports_items=body.supports_items,
                ),
                is_active=body.is_active,
            )
        )
    except Exception as exc:
        mapped = _map_domain_error(exc)
        if mapped.status_code == 400 and isinstance(exc, InvalidOperationTypeError):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise mapped from exc
    return _to_operation_type_catalog_item(item)


@router.post(
    "",
    response_model=OperationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def create_operation(
    body: CreateOperationRequest,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    use_case: CreateOperationUseCase = Depends(get_create_operation_use_case),
    scraper_job_buffer: ScraperJobBuffer = Depends(get_scraper_job_buffer),
    job_runner: FairScraperJobRunner = Depends(get_fair_scraper_job_runner),
    db: Session = Depends(get_db),
) -> OperationResponse:
    try:
        result = use_case.execute(
            CreateOperationCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                operation_type=body.operation_type,
                title=body.title,
                description=body.description,
                source_kind=body.source_kind,
                source_ids=body.source_ids,
                source_config=body.source_config,
                type_config=body.type_config,
                run_settings=body.run_settings,
                priority=body.priority,
                status=body.status,
                start_immediately=body.start_immediately,
            )
        )
    except (
        ForbiddenError,
        InvalidOperationConfigError,
        InvalidOperationTitleError,
        InvalidOperationTypeError,
        InvalidSourceKindError,
        HandlerNotRegisteredError,
        InvalidOperationStatusTransitionError,
        InvalidRunStatusTransitionError,
    ) as exc:
        raise _map_domain_error(exc) from exc
    db.commit()
    _schedule_scraper_jobs(
        background_tasks=background_tasks,
        scraper_job_buffer=scraper_job_buffer,
        job_runner=job_runner,
    )
    return _to_operation_response(result)


@router.get(
    "",
    response_model=OperationListResponse,
    responses={403: {"model": ErrorResponse}},
)
def list_operations(
    request: Request,
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListOperationsUseCase = Depends(get_list_operations_use_case),
    operation_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: Annotated[
        int,
        Query(ge=1, le=100, validation_alias=AliasChoices("pageSize", "page_size")),
    ] = 25,
    sort: Annotated[
        str | None,
        Query(validation_alias=AliasChoices("sort_by", "sort")),
    ] = None,
    direction: Annotated[
        str | None,
        Query(validation_alias=AliasChoices("sort_dir", "sort_order", "direction")),
    ] = None,
):
    _ = auth
    resolved_page_size = resolve_page_size_from_request(request, page_size)
    list_query = parse_list_query(
        page=page,
        page_size=resolved_page_size,
        search=search,
        sort=sort,
        direction=direction,
        allowed_sort_fields=ALLOWED_SORT_FIELDS,
        default_sort=DEFAULT_SORT_FIELD,
        default_direction=DEFAULT_SORT_DIRECTION,
    )
    items, page_result = use_case.execute(
        ListOperationsQuery(
            organization_id=auth.organization_id,
            operation_type=operation_type,
            status=status_filter,
            search=list_query.search,
            page=list_query.page,
            page_size=list_query.page_size,
            sort_by=list_query.sort_by,
            sort_dir=list_query.sort_dir,
        )
    )
    return standard_list_from_result(
        page_result,
        sort_field=list_query.sort_by,
        sort_direction=list_query.sort_dir,
        filters={
            "operation_type": operation_type,
            "status": status_filter,
            "search": list_query.search,
        },
    ).model_copy(update={"items": [_to_operation_response(item) for item in items]})


@router.get(
    "/{operation_id}",
    response_model=OperationDetailResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_operation(
    operation_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    use_case: GetOperationUseCase = Depends(get_get_operation_use_case),
) -> OperationDetailResponse:
    try:
        result = use_case.execute(
            GetOperationQuery(
                organization_id=auth.organization_id,
                operation_id=operation_id,
            )
        )
    except OperationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return OperationDetailResponse(
        operation=_to_operation_response(result.operation),
        runs=[_to_run_response(run) for run in result.runs],
    )


@router.get(
    "/{operation_id}/runs",
    response_model=OperationRunListResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_operation_runs(
    request: Request,
    operation_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListOperationRunsUseCase = Depends(get_list_operation_runs_use_case),
    page: int = Query(default=1, ge=1),
    page_size: Annotated[
        int,
        Query(ge=1, le=100, validation_alias=AliasChoices("pageSize", "page_size")),
    ] = 25,
    sort: Annotated[
        str | None,
        Query(validation_alias=AliasChoices("sort_by", "sort")),
    ] = None,
    direction: Annotated[
        str | None,
        Query(validation_alias=AliasChoices("sort_dir", "sort_order", "direction")),
    ] = None,
):
    resolved_page_size = resolve_page_size_from_request(request, page_size)
    list_query = parse_list_query(
        page=page,
        page_size=resolved_page_size,
        sort=sort,
        direction=direction,
        allowed_sort_fields=RUN_ALLOWED_SORT_FIELDS,
        default_sort="created_at",
        default_direction="desc",
    )
    try:
        items, page_result = use_case.execute(
            ListOperationRunsQuery(
                organization_id=auth.organization_id,
                operation_id=operation_id,
                page=list_query.page,
                page_size=list_query.page_size,
                sort_by=list_query.sort_by,
                sort_dir=list_query.sort_dir,
            )
        )
    except OperationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return standard_list_from_result(
        page_result,
        sort_field=list_query.sort_by,
        sort_direction=list_query.sort_dir,
    ).model_copy(update={"items": [_to_run_response(item) for item in items]})


@router.post(
    "/{operation_id}/start",
    response_model=OperationResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def start_operation(
    operation_id: UUID,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    use_case: StartOperationUseCase = Depends(get_start_operation_use_case),
    scraper_job_buffer: ScraperJobBuffer = Depends(get_scraper_job_buffer),
    job_runner: FairScraperJobRunner = Depends(get_fair_scraper_job_runner),
    db: Session = Depends(get_db),
) -> OperationResponse:
    try:
        result = use_case.execute(
            StartOperationCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                operation_id=operation_id,
            )
        )
    except (
        ForbiddenError,
        OperationNotFoundError,
        HandlerNotRegisteredError,
        InvalidOperationConfigError,
        InvalidOperationStatusTransitionError,
        InvalidRunStatusTransitionError,
    ) as exc:
        raise _map_domain_error(exc) from exc
    db.commit()
    _schedule_scraper_jobs(
        background_tasks=background_tasks,
        scraper_job_buffer=scraper_job_buffer,
        job_runner=job_runner,
    )
    return _to_operation_response(result)


@router.post(
    "/{operation_id}/cancel",
    response_model=OperationResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def cancel_operation(
    operation_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    use_case: CancelOperationUseCase = Depends(get_cancel_operation_use_case),
    run_id: UUID | None = Query(default=None),
) -> OperationResponse:
    try:
        result = use_case.execute(
            CancelOperationCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                operation_id=operation_id,
                run_id=run_id,
            )
        )
    except (
        ForbiddenError,
        OperationNotFoundError,
        OperationRunNotFoundError,
        HandlerNotRegisteredError,
        HandlerCapabilityNotSupportedError,
        InvalidOperationStatusTransitionError,
        InvalidRunStatusTransitionError,
    ) as exc:
        raise _map_domain_error(exc) from exc
    return _to_operation_response(result)


@router.post(
    "/{operation_id}/retry",
    response_model=OperationResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def retry_operation(
    operation_id: UUID,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    use_case: RetryOperationUseCase = Depends(get_retry_operation_use_case),
    scraper_job_buffer: ScraperJobBuffer = Depends(get_scraper_job_buffer),
    job_runner: FairScraperJobRunner = Depends(get_fair_scraper_job_runner),
    db: Session = Depends(get_db),
    run_id: UUID | None = Query(default=None),
) -> OperationResponse:
    try:
        result = use_case.execute(
            RetryOperationCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                operation_id=operation_id,
                run_id=run_id,
            )
        )
    except (
        ForbiddenError,
        OperationNotFoundError,
        OperationRunNotFoundError,
        HandlerNotRegisteredError,
        HandlerCapabilityNotSupportedError,
        InvalidOperationConfigError,
        InvalidOperationStatusTransitionError,
        InvalidRunStatusTransitionError,
    ) as exc:
        raise _map_domain_error(exc) from exc
    db.commit()
    _schedule_scraper_jobs(
        background_tasks=background_tasks,
        scraper_job_buffer=scraper_job_buffer,
        job_runner=job_runner,
    )
    return _to_operation_response(result)

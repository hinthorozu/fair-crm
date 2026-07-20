from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AliasChoices

from app.api.dependencies.list_query import parse_list_query, resolve_page_size_from_request
from app.api.list_helpers import standard_list_from_result
from app.modules.fairs.application.list_fairs import (
    ALLOWED_SORT_FIELDS,
    DEFAULT_SORT_DIRECTION,
    DEFAULT_SORT_FIELD,
)

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.fairs.api.dependencies import (
    get_archive_fair_use_case,
    get_auth_context,
    get_create_fair_use_case,
    get_fair_scraper_job_runner,
    get_enrichment_run_job_runner,
    get_get_fair_use_case,
    get_list_fairs_use_case,
    get_restore_fair_use_case,
    get_run_fair_enrichment_use_case,
    get_run_fair_scraper_use_case,
    get_update_fair_use_case,
    require_read_permission,
    require_scraper_run_permission,
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
from app.modules.fairs.application.run_fair_enrichment import RunFairEnrichmentCommand, RunFairEnrichmentUseCase
from app.modules.fairs.application.run_fair_scraper import RunFairScraperCommand, RunFairScraperUseCase
from app.modules.fairs.application.update_fair import UpdateFairUseCase
from app.modules.fairs.domain.exceptions import (
    FairAlreadyArchivedError,
    FairNotArchivedError,
    FairEnrichmentNoCandidatesError,
    FairNotFoundError,
    FairScraperAdapterNotConfiguredError,
    FairScraperNotConfiguredError,
    FairScraperUrlNotConfiguredError,
    InvalidFairAdapterConfigError,
    InvalidFairDateRangeError,
    InvalidFairNameError,
    InvalidFairSourceUrlError,
)
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.scraper.api.schemas import EnrichmentRunRequest, ScraperRunHistoryResponse
from app.modules.scraper.application.enrichment_run_job_runner import EnrichmentRunJobCommand, EnrichmentRunJobRunner
from app.modules.scraper.application.fair_scraper_job_runner import FairScraperJobCommand, FairScraperJobRunner
from app.modules.scraper.core.browser_service import BrowserConfig
from app.modules.scraper.core.playwright_availability import playwright_browser_unavailable_message
from app.shared.background_jobs import run_blocking_background_task
from sqlalchemy.orm import Session

from app.db.session import get_db

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
    except InvalidFairAdapterConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidFairSourceUrlError as exc:
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
    country: str | None = Query(default=None, max_length=100),
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
    sort_by: Annotated[str | None, Query(include_in_schema=False)] = None,
    direction: Annotated[
        str | None,
        Query(
            pattern="^(?i)(asc|desc)$",
            validation_alias=AliasChoices("sort_order", "sort_dir", "direction"),
        ),
    ] = None,
    sort_dir: Annotated[str | None, Query(include_in_schema=False)] = None,
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

    result = use_case.execute(
        ListFairsQuery(
            organization_id=auth.organization_id,
            status=list_status,
            include_archived=list_include_archived,
            country=country.strip() if country and country.strip() else None,
            search=list_query.search,
            page=list_query.page,
            page_size=list_query.page_size,
            sort_by=list_query.sort_by,
            sort_dir=list_query.sort_dir,
        )
    )
    filters: dict = {}
    if list_query.search:
        filters["search"] = list_query.search
    if list_status is not None:
        filters["status"] = list_status.value
    if country and country.strip():
        filters["country"] = country.strip()

    return standard_list_from_result(
        result,
        sort_field=list_query.sort_by,
        sort_direction=list_query.sort_dir,
        filters=filters,
    ).model_copy(
        update={"items": [_to_response(item) for item in result.items]},
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
    except InvalidFairAdapterConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidFairSourceUrlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.post(
    "/{fair_id}/run",
    response_model=ScraperRunHistoryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def run_fair_scraper(
    fair_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_scraper_run_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: RunFairScraperUseCase = Depends(get_run_fair_scraper_use_case),
    job_runner: FairScraperJobRunner = Depends(get_fair_scraper_job_runner),
) -> ScraperRunHistoryResponse:
    unavailable = playwright_browser_unavailable_message(BrowserConfig.from_settings(get_settings()))
    if unavailable:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=unavailable)
    try:
        run = use_case.execute(
            RunFairScraperCommand(
                organization_id=auth.organization_id,
                fair_id=fair_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FairNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (FairScraperAdapterNotConfiguredError, FairScraperUrlNotConfiguredError, FairScraperNotConfiguredError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    access_token = _access_token(credentials)
    background_tasks.add_task(
        run_blocking_background_task,
        job_runner.run_fair_scraper,
        FairScraperJobCommand(
            run_id=run.id,
            organization_id=auth.organization_id,
            fair_id=fair_id,
            user_id=auth.user_id,
            access_token=access_token,
        ),
    )
    return ScraperRunHistoryResponse.from_entity(run)


@router.post(
    "/{fair_id}/scraper-runs",
    response_model=ScraperRunHistoryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
    include_in_schema=True,
)
def run_fair_scraper_alias(
    fair_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_scraper_run_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: RunFairScraperUseCase = Depends(get_run_fair_scraper_use_case),
    job_runner: FairScraperJobRunner = Depends(get_fair_scraper_job_runner),
) -> ScraperRunHistoryResponse:
    """Alias for fair automation scraper run (same as POST /fairs/{id}/run)."""
    return run_fair_scraper(
        fair_id=fair_id,
        background_tasks=background_tasks,
        db=db,
        auth=auth,
        credentials=credentials,
        use_case=use_case,
        job_runner=job_runner,
    )


@router.post(
    "/{fair_id}/contact-enrichment/run",
    response_model=ScraperRunHistoryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
    summary="Fuar katılımcıları için iletişim zenginleştirme çalıştır",
)
def run_fair_contact_enrichment(
    fair_id: UUID,
    body: EnrichmentRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_scraper_run_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: RunFairEnrichmentUseCase = Depends(get_run_fair_enrichment_use_case),
    job_runner: EnrichmentRunJobRunner = Depends(get_enrichment_run_job_runner),
) -> ScraperRunHistoryResponse:
    try:
        run = use_case.execute(
            RunFairEnrichmentCommand(
                organization_id=auth.organization_id,
                fair_id=fair_id,
                limit=body.limit,
                include_existing_email=body.include_existing_email,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FairNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FairEnrichmentNoCandidatesError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    access_token = _access_token(credentials)
    background_tasks.add_task(
        run_blocking_background_task,
        job_runner.run_enrichment,
        EnrichmentRunJobCommand(
            run_id=run.id,
            organization_id=auth.organization_id,
            adapter_key=run.adapter_key,
            user_id=auth.user_id,
            access_token=access_token,
            limit=body.limit,
            requested_fields=body.requested_fields,
            dry_run=body.dry_run,
            max_pages=body.max_pages or 10,
            fair_id=fair_id,
            ignore_previous_scan_state=True,
            include_existing_email=body.include_existing_email,
        ),
    )
    return ScraperRunHistoryResponse.from_entity(run)


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

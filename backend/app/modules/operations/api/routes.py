from dataclasses import asdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AliasChoices, ValidationError
from sqlalchemy.orm import Session

from app.api.dependencies.list_query import parse_list_query, resolve_page_size_from_request
from app.api.list_helpers import standard_list_from_result
from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.fairs.api.dependencies import get_fair_scraper_job_runner
from app.modules.operations.api.dependencies import (
    BulkEmailJobBuffer,
    ScraperJobBuffer,
    get_auth_context,
    get_bulk_email_job_buffer,
    get_cancel_operation_use_case,
    get_create_operation_use_case,
    get_get_operation_use_case,
    get_list_operation_runs_use_case,
    get_list_operation_types_use_case,
    get_list_operations_use_case,
    get_preview_bulk_email_operation_use_case,
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
    BulkEmailOperationLogLineResponse,
    BulkEmailOperationLogsResponse,
    BulkEmailOperationMailPreviewResponse,
    BulkEmailOperationPreviewPayload,
    BulkEmailOperationPreviewRecipientResponse,
    BulkEmailOperationPreviewResponse,
    BulkEmailOperationRecipientRowResponse,
    BulkEmailOperationRecipientSummaryResponse,
    BulkEmailOperationRecipientsResponse,
    BulkEmailOperationSendPayload,
    BulkEmailOperationSendResponse,
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


def _schedule_bulk_email_jobs(
    *,
    background_tasks: BackgroundTasks,
    bulk_email_job_buffer: BulkEmailJobBuffer,
) -> None:
    from app.modules.fair_emails.application.process_batch import process_fair_email_batch

    for command in bulk_email_job_buffer.drain():
        background_tasks.add_task(
            run_blocking_background_task,
            process_fair_email_batch,
            command.batch_id,
            command.organization_id,
        )


def _schedule_background_jobs(
    *,
    background_tasks: BackgroundTasks,
    scraper_job_buffer: ScraperJobBuffer,
    bulk_email_job_buffer: BulkEmailJobBuffer,
    job_runner: FairScraperJobRunner,
) -> None:
    _schedule_scraper_jobs(
        background_tasks=background_tasks,
        scraper_job_buffer=scraper_job_buffer,
        job_runner=job_runner,
    )
    _schedule_bulk_email_jobs(
        background_tasks=background_tasks,
        bulk_email_job_buffer=bulk_email_job_buffer,
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
    bulk_email_job_buffer: BulkEmailJobBuffer = Depends(get_bulk_email_job_buffer),
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
    _schedule_background_jobs(
        background_tasks=background_tasks,
        scraper_job_buffer=scraper_job_buffer,
        bulk_email_job_buffer=bulk_email_job_buffer,
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
    bulk_email_job_buffer: BulkEmailJobBuffer = Depends(get_bulk_email_job_buffer),
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
    _schedule_background_jobs(
        background_tasks=background_tasks,
        scraper_job_buffer=scraper_job_buffer,
        bulk_email_job_buffer=bulk_email_job_buffer,
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
    bulk_email_job_buffer: BulkEmailJobBuffer = Depends(get_bulk_email_job_buffer),
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
    _schedule_background_jobs(
        background_tasks=background_tasks,
        scraper_job_buffer=scraper_job_buffer,
        bulk_email_job_buffer=bulk_email_job_buffer,
        job_runner=job_runner,
    )
    return _to_operation_response(result)


@router.post(
    "/bulk-email/preview",
    response_model=BulkEmailOperationPreviewResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def preview_bulk_email_operation(
    payload_json: str = Form(..., alias="payload"),
    excel_file: UploadFile | None = File(None),
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    use_case=Depends(get_preview_bulk_email_operation_use_case),
) -> BulkEmailOperationPreviewResponse:
    """Preview recipients + rendered mail for the operations bulk-email wizard (no send)."""
    from app.modules.fair_emails.application.preview_bulk_email_operation import (
        PreviewBulkEmailOperationCommand,
    )
    from app.modules.fair_emails.domain.exceptions import FairNotEligibleForBulkEmailError
    from app.modules.fair_emails.domain.value_objects import RecipientOptions
    from app.modules.fairs.domain.exceptions import FairNotFoundError
    from app.modules.imports.domain.exceptions import InvalidImportFileError
    from app.modules.mail_templates.domain.exceptions import (
        MailTemplateAlreadyDeletedError,
        MailTemplateInactiveForTestError,
        MailTemplateNotFoundError,
        MailTemplateRenderError,
    )
    from app.modules.smtp.domain.exceptions import (
        SmtpAccountAlreadyDeletedError,
        SmtpAccountNotFoundError,
    )

    try:
        payload = BulkEmailOperationPreviewPayload.model_validate_json(payload_json)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail="Geçersiz önizleme isteği") from exc

    excel_bytes: bytes | None = None
    if excel_file is not None and excel_file.filename:
        name = excel_file.filename.lower()
        if not name.endswith(".xlsx"):
            raise HTTPException(status_code=400, detail="Yalnızca .xlsx dosyası desteklenir")
        excel_bytes = await excel_file.read()

    opts = payload.recipient_options
    try:
        result = use_case.execute(
            PreviewBulkEmailOperationCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                source_type=payload.source_type,
                template_id=payload.template_id,
                smtp_account_id=payload.smtp_account_id,
                subject_override=payload.subject_override,
                manual_emails=payload.manual_emails,
                excel_bytes=excel_bytes,
                fair_ids=list(payload.fair_ids),
                country_filter=payload.country_filter,
                city_filter=payload.city_filter,
                company_name_contains=payload.company_name_contains,
                recipient_options=RecipientOptions(
                    include_customer_emails=opts.include_customer_emails,
                    include_contact_emails=opts.include_contact_emails,
                    skip_no_email=opts.skip_no_email,
                    exclude_inactive=opts.exclude_inactive,
                    dedupe_emails=opts.dedupe_emails,
                ),
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FairNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        FairNotEligibleForBulkEmailError,
        InvalidImportFileError,
        MailTemplateAlreadyDeletedError,
        MailTemplateInactiveForTestError,
        MailTemplateNotFoundError,
        MailTemplateRenderError,
        SmtpAccountAlreadyDeletedError,
        SmtpAccountNotFoundError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    recipients = result.recipients
    mail = result.mail
    return BulkEmailOperationPreviewResponse(
        recipients=BulkEmailOperationRecipientSummaryResponse(
            source_type=recipients.source_type,  # type: ignore[arg-type]
            total_found=recipients.total_found,
            valid_email_count=recipients.valid_email_count,
            duplicate_count=recipients.duplicate_count,
            invalid_count=recipients.invalid_count,
            deduped_recipient_count=recipients.deduped_recipient_count,
            skipped_count=recipients.skipped_count,
            selected_fair_count=recipients.selected_fair_count,
            selected_fair_names=recipients.selected_fair_names,
            total_customers=recipients.total_customers,
            total_contacts=recipients.total_contacts,
            recipients=[
                BulkEmailOperationPreviewRecipientResponse(
                    recipient_key=item.recipient_key,
                    email=item.email,
                    source=item.source,
                    status=item.status,
                    skip_reason=item.skip_reason,
                    recipient_name=item.recipient_name,
                    company_name=item.company_name,
                    fair_id=item.fair_id,
                    fair_name=item.fair_name,
                    customer_id=item.customer_id,
                    contact_id=item.contact_id,
                    participation_id=item.participation_id,
                )
                for item in recipients.recipients
            ],
        ),
        mail=BulkEmailOperationMailPreviewResponse(
            template_id=mail.template_id,
            template_name=mail.template_name,
            smtp_account_id=mail.smtp_account_id,
            smtp_account_name=mail.smtp_account_name,
            rendered_subject=mail.rendered_subject,
            body_html=mail.body_html,
            body_text=mail.body_text,
        ),
    )

@router.post(
    "/bulk-email/send",
    response_model=BulkEmailOperationSendResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def send_bulk_email_operation(
    background_tasks: BackgroundTasks,
    payload_json: str = Form(..., alias="payload"),
    excel_file: UploadFile | None = File(None),
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    use_case: CreateOperationUseCase = Depends(get_create_operation_use_case),
    scraper_job_buffer: ScraperJobBuffer = Depends(get_scraper_job_buffer),
    bulk_email_job_buffer: BulkEmailJobBuffer = Depends(get_bulk_email_job_buffer),
    job_runner: FairScraperJobRunner = Depends(get_fair_scraper_job_runner),
    db: Session = Depends(get_db),
) -> BulkEmailOperationSendResponse:
    """Create + start a bulk_email operation (multipart like preview)."""
    from app.modules.fair_emails.application.excel_email_extract import extract_email_tokens_from_xlsx
    from app.modules.fair_emails.domain.exceptions import FairBulkEmailRecipientNotFoundError
    from app.modules.imports.domain.exceptions import InvalidImportFileError
    from app.modules.mail_templates.domain.exceptions import (
        MailTemplateAlreadyDeletedError,
        MailTemplateInactiveForTestError,
        MailTemplateNotFoundError,
    )
    from app.modules.smtp.domain.exceptions import (
        SmtpAccountAlreadyDeletedError,
        SmtpAccountNotFoundError,
    )

    try:
        payload = BulkEmailOperationSendPayload.model_validate_json(payload_json)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail="Geçersiz gönderim isteği") from exc

    # Soft idempotency: same client_token returns the existing operation instead of a duplicate send.
    if payload.client_token:
        from app.modules.operations.infrastructure.persistence.models import OperationModel

        token = payload.client_token.strip()
        if token:
            recent = (
                db.query(OperationModel)
                .filter(
                    OperationModel.organization_id == auth.organization_id,
                    OperationModel.operation_type == "bulk_email",
                )
                .order_by(OperationModel.created_at.desc())
                .limit(50)
                .all()
            )
            for row in recent:
                cfg = row.type_config if isinstance(row.type_config, dict) else {}
                if str(cfg.get("client_token") or "") == token:
                    existing_batch = None
                    try:
                        existing_batch, _ = _resolve_bulk_email_batch(
                            db, auth.organization_id, row.id
                        )
                    except HTTPException:
                        existing_batch = None
                    return BulkEmailOperationSendResponse(
                        operation_id=row.id,
                        batch_id=existing_batch.id if existing_batch else None,
                        status=row.status,
                        total_count=existing_batch.total_count if existing_batch else 0,
                        message="Toplu mail operasyonu zaten başlatılmış.",
                    )

    excel_tokens: list[str] = []
    if excel_file is not None and excel_file.filename:
        name = excel_file.filename.lower()
        if not name.endswith(".xlsx"):
            raise HTTPException(status_code=400, detail="Yalnızca .xlsx dosyası desteklenir")
        excel_bytes = await excel_file.read()
        try:
            excel_tokens = extract_email_tokens_from_xlsx(excel_bytes)
        except InvalidImportFileError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    opts = payload.recipient_options
    source_type = payload.source_type
    if source_type == "fair_list":
        source_kind = "fair"
        source_ids = list(payload.fair_ids)
    else:
        source_kind = "manual_selection"
        source_ids = []

    type_config: dict = {
        "source_type": source_type,
        "template_id": str(payload.template_id),
        "smtp_account_id": str(payload.smtp_account_id),
        "subject": payload.subject,
        "manual_emails": payload.manual_emails,
        "excel_email_tokens": excel_tokens,
        "fair_ids": [str(item) for item in payload.fair_ids],
        "country_filter": payload.country_filter,
        "city_filter": payload.city_filter,
        "company_name_contains": payload.company_name_contains,
        "recipient_options": {
            "include_customer_emails": opts.include_customer_emails,
            "include_contact_emails": opts.include_contact_emails,
            "skip_no_email": opts.skip_no_email,
            "exclude_inactive": opts.exclude_inactive,
            "dedupe_emails": opts.dedupe_emails,
        },
    }
    if payload.client_token:
        type_config["client_token"] = payload.client_token

    title = (payload.title or "").strip() or (
        "Toplu e-posta (manuel)" if source_type == "manual" else "Toplu e-posta (fuar listesi)"
    )

    try:
        result = use_case.execute(
            CreateOperationCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                operation_type="bulk_email",
                title=title,
                description=None,
                source_kind=source_kind,
                source_ids=source_ids,
                source_config={},
                type_config=type_config,
                run_settings={},
                priority="normal",
                status="ready",
                start_immediately=True,
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
        FairBulkEmailRecipientNotFoundError,
        MailTemplateAlreadyDeletedError,
        MailTemplateInactiveForTestError,
        MailTemplateNotFoundError,
        SmtpAccountAlreadyDeletedError,
        SmtpAccountNotFoundError,
        ValueError,
    ) as exc:
        raise _map_domain_error(exc) from exc

    db.commit()
    _schedule_background_jobs(
        background_tasks=background_tasks,
        scraper_job_buffer=scraper_job_buffer,
        bulk_email_job_buffer=bulk_email_job_buffer,
        job_runner=job_runner,
    )

    batch_id = None
    total_count = 0
    if result.latest_run is not None:
        details = getattr(result.latest_run, "error_details", None) or {}
        payload_result = details.get("result") if isinstance(details, dict) else None
        if isinstance(payload_result, dict):
            raw_batch = payload_result.get("batch_id")
            if raw_batch:
                try:
                    batch_id = UUID(str(raw_batch))
                except (TypeError, ValueError):
                    batch_id = None
            total_count = int(payload_result.get("will_send_count") or payload_result.get("total_count") or 0)

    return BulkEmailOperationSendResponse(
        operation_id=result.id,
        batch_id=batch_id,
        status=result.status,
        total_count=total_count,
        message="Toplu mail operasyonu başlatıldı.",
    )


def _resolve_bulk_email_batch(db: Session, organization_id: UUID, operation_id: UUID):
    from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
        SqlAlchemyFairEmailBatchRepository,
    )
    from app.modules.operations.infrastructure.handlers.bulk_email_operation_sync import (
        resolve_batch_for_operation,
    )
    from app.modules.operations.infrastructure.repositories.operation_repository import (
        SqlAlchemyOperationRepository,
    )
    from app.modules.operations.infrastructure.repositories.operation_run_repository import (
        SqlAlchemyOperationRunRepository,
    )

    operation = SqlAlchemyOperationRepository(db).get_by_id(organization_id, operation_id)
    if operation is None:
        raise HTTPException(status_code=404, detail="Operation not found")
    if operation.operation_type != "bulk_email":
        raise HTTPException(status_code=400, detail="Operation is not a bulk_email operation")

    latest_run = None
    if operation.latest_run_id is not None:
        latest_run = SqlAlchemyOperationRunRepository(db).get_by_id(
            organization_id, operation.latest_run_id
        )
    batch = resolve_batch_for_operation(
        db,
        organization_id=organization_id,
        operation_id=operation_id,
        run=latest_run,
    )
    if batch is None:
        raise HTTPException(status_code=404, detail="Bulk email batch not found for operation")
    return batch, SqlAlchemyFairEmailBatchRepository(db)


@router.get(
    "/{operation_id}/bulk-email/recipients",
    response_model=BulkEmailOperationRecipientsResponse,
    responses={400: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def list_bulk_email_operation_recipients(
    operation_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    db: Session = Depends(get_db),
) -> BulkEmailOperationRecipientsResponse:
    batch, repo = _resolve_bulk_email_batch(db, auth.organization_id, operation_id)
    items = repo.list_outbox_for_batch(auth.organization_id, batch.id)
    return BulkEmailOperationRecipientsResponse(
        batch_id=batch.id,
        items=[
            BulkEmailOperationRecipientRowResponse(
                id=item.id,
                email=item.email,
                company_name=item.company_name,
                recipient_name=item.recipient_name,
                source=item.source,
                status=item.status,
                error_message=item.error_message,
                send_attempt=item.send_attempt,
                sent_at=item.sent_at,
                customer_id=item.customer_id,
                contact_id=item.contact_id,
                participation_id=item.participation_id,
                fair_name=item.fair_name,
            )
            for item in items
        ],
    )


@router.get(
    "/{operation_id}/bulk-email/logs",
    response_model=BulkEmailOperationLogsResponse,
    responses={400: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def list_bulk_email_operation_logs(
    operation_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    db: Session = Depends(get_db),
) -> BulkEmailOperationLogsResponse:
    from app.modules.operations.infrastructure.repositories.operation_repository import (
        SqlAlchemyOperationRepository,
    )
    from app.modules.operations.infrastructure.repositories.operation_run_repository import (
        SqlAlchemyOperationRunRepository,
    )

    batch, repo = _resolve_bulk_email_batch(db, auth.organization_id, operation_id)
    items = repo.list_outbox_for_batch(auth.organization_id, batch.id)
    lines: list[BulkEmailOperationLogLineResponse] = []

    started_at = batch.created_at
    if items:
        earliest = min((item.created_at for item in items if item.created_at is not None), default=None)
        if earliest is not None and (started_at is None or earliest < started_at):
            started_at = earliest

    lines.append(
        BulkEmailOperationLogLineResponse(
            at=started_at,
            level="info",
            message="Toplu e-posta gönderimi başladı",
            outbox_id=None,
            email=None,
            status=None,
        )
    )
    lines.append(
        BulkEmailOperationLogLineResponse(
            at=started_at,
            level="info",
            message=f"{batch.total_count} alıcı kuyruğa alındı",
            outbox_id=None,
            email=None,
            status=None,
        )
    )

    operation = SqlAlchemyOperationRepository(db).get_by_id(auth.organization_id, operation_id)
    latest_run = None
    if operation is not None and operation.latest_run_id is not None:
        latest_run = SqlAlchemyOperationRunRepository(db).get_by_id(
            auth.organization_id, operation.latest_run_id
        )
    run_result: dict = {}
    if latest_run is not None and isinstance(latest_run.error_details, dict):
        raw_result = latest_run.error_details.get("result")
        if isinstance(raw_result, dict):
            run_result = raw_result
    if run_result.get("retry_failed_only"):
        retried = int(run_result.get("retried_count") or 0)
        retry_at = latest_run.started_at if latest_run is not None else started_at
        lines.append(
            BulkEmailOperationLogLineResponse(
                at=retry_at,
                level="info",
                message="Gönderilmeyenler için manuel tekrar gönderim başlatıldı",
                outbox_id=None,
                email=None,
                status=None,
            )
        )
        lines.append(
            BulkEmailOperationLogLineResponse(
                at=retry_at,
                level="info",
                message=f"{retried} kayıt yeniden kuyruğa alındı",
                outbox_id=None,
                email=None,
                status=None,
            )
        )

    sent_count = 0
    failed_count = 0
    for item in items:
        if item.status == "sent":
            sent_count += 1
            lines.append(
                BulkEmailOperationLogLineResponse(
                    at=item.sent_at or item.updated_at,
                    level="info",
                    message=f"{item.email} gönderildi",
                    outbox_id=item.id,
                    email=item.email,
                    status=item.status,
                )
            )
        elif item.status == "failed":
            failed_count += 1
            err = item.error_message or "bilinmeyen hata"
            if "sending_timeout" in err.lower():
                message = (
                    f"{item.email} gönderilemedi: {err} "
                    "(belirsiz gönderim durumu — SMTP kabul etmiş olabilir)"
                )
            else:
                message = f"{item.email} gönderilemedi: {err}"
            lines.append(
                BulkEmailOperationLogLineResponse(
                    at=item.updated_at,
                    level="error",
                    message=message,
                    outbox_id=item.id,
                    email=item.email,
                    status=item.status,
                )
            )
        else:
            lines.append(
                BulkEmailOperationLogLineResponse(
                    at=item.updated_at,
                    level="info",
                    message=f"{item.status}: {item.email}",
                    outbox_id=item.id,
                    email=item.email,
                    status=item.status,
                )
            )

    processed = sent_count + failed_count
    if processed > 0 and batch.total_count > 0:
        lines.append(
            BulkEmailOperationLogLineResponse(
                at=max((item.updated_at for item in items if item.updated_at is not None), default=started_at),
                level="info",
                message=f"{processed}/{batch.total_count} işlendi",
                outbox_id=None,
                email=None,
                status=None,
            )
        )

    terminal_batch = batch.status in {"completed", "failed", "cancelled"}
    still_inflight = any(item.status in {"pending", "sending"} for item in items)
    if terminal_batch or (items and not still_inflight):
        end_at = max(
            (item.updated_at for item in items if item.updated_at is not None),
            default=started_at,
        )
        lines.append(
            BulkEmailOperationLogLineResponse(
                at=end_at,
                level="info",
                message=f"{sent_count} gönderildi · {failed_count} başarısız",
                outbox_id=None,
                email=None,
                status=None,
            )
        )
        lines.append(
            BulkEmailOperationLogLineResponse(
                at=end_at,
                level="info",
                message="İşlem tamamlandı",
                outbox_id=None,
                email=None,
                status=None,
            )
        )

    lines.sort(key=lambda line: (line.at is None, line.at))
    return BulkEmailOperationLogsResponse(batch_id=batch.id, items=lines)


@router.get(
    "/{operation_id}/bulk-email/export",
    responses={400: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def export_bulk_email_operation_recipients(
    operation_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    db: Session = Depends(get_db),
    format: str = Query(default="json", pattern="^(json|excel)$"),
):
    from fastapi.responses import JSONResponse, StreamingResponse
    import io
    import json

    batch, repo = _resolve_bulk_email_batch(db, auth.organization_id, operation_id)
    items = repo.list_outbox_for_batch(auth.organization_id, batch.id)
    rows = [
        {
            "id": str(item.id),
            "email": item.email,
            "company_name": item.company_name,
            "recipient_name": item.recipient_name,
            "source": item.source,
            "fair": item.fair_name,
            "status": item.status,
            "error_message": item.error_message,
            "send_attempt": item.send_attempt,
            "sent_at": item.sent_at.isoformat() if item.sent_at else None,
            "customer_id": str(item.customer_id) if item.customer_id else None,
            "contact_id": str(item.contact_id) if item.contact_id else None,
            "participation_id": str(item.participation_id) if item.participation_id else None,
        }
        for item in items
    ]
    if format == "json":
        return JSONResponse(content={"batch_id": str(batch.id), "items": rows})

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "recipients"
    headers = list(rows[0].keys()) if rows else [
        "id",
        "email",
        "company_name",
        "recipient_name",
        "source",
        "fair",
        "status",
        "error_message",
        "send_attempt",
        "sent_at",
        "customer_id",
        "contact_id",
        "participation_id",
    ]
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h) for h in headers])
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="bulk-email-{batch.id}.xlsx"'
        },
    )


@router.post(
    "/{operation_id}/bulk-email/retry-failed",
    response_model=OperationResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def retry_bulk_email_operation_failed(
    operation_id: UUID,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    use_case: RetryOperationUseCase = Depends(get_retry_operation_use_case),
    scraper_job_buffer: ScraperJobBuffer = Depends(get_scraper_job_buffer),
    bulk_email_job_buffer: BulkEmailJobBuffer = Depends(get_bulk_email_job_buffer),
    job_runner: FairScraperJobRunner = Depends(get_fair_scraper_job_runner),
    db: Session = Depends(get_db),
) -> OperationResponse:
    """Retry failed recipients via RetryOperationUseCase (handler.on_retry)."""
    try:
        result = use_case.execute(
            RetryOperationCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                operation_id=operation_id,
                run_id=None,
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
    _schedule_background_jobs(
        background_tasks=background_tasks,
        scraper_job_buffer=scraper_job_buffer,
        bulk_email_job_buffer=bulk_email_job_buffer,
        job_runner=job_runner,
    )
    return _to_operation_response(result)

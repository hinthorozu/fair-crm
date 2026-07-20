"""HTTP routes for Adapter Yönetimi (adapter manifest discovery and dashboard)."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.shared.background_jobs import run_blocking_background_task

from app.modules.scraper.api.dependencies import (
    get_adapter_engine_service,
    get_adapter_linked_fair_service,
    get_adapter_test_run_job_runner,
    get_default_scraper_dashboard_service,
    get_default_scraper_manager,
    get_delete_adapter_use_case,
    get_enrichment_run_job_runner,
    get_run_adapter_test_use_case,
    get_run_enrichment_use_case,
    get_scraper_adapter_service,
    get_scraper_run_history_service,
    get_scraper_run_log_service,
    require_create_permission,
    require_delete_permission,
    require_download_permission,
    require_read_permission,
    require_run_permission,
    require_update_permission,
)
from app.modules.scraper.api.dependencies import bearer_scheme
from app.modules.scraper.api.schemas import (
    AdapterDetailResponse,
    AdapterDeletePreviewResponse,
    AdapterDeletePreviewActiveRunResponse,
    AdapterEngineListResponse,
    AdapterEngineResponse,
    AdapterLinkedFairListResponse,
    AdapterLinkedFairResponse,
    AdapterListItemResponse,
    AdapterListResponse,
    AdapterTestRunRequest,
    EnrichmentRunRequest,
    EnrichmentStateResetRequest,
    EnrichmentStateResetResponse,
    CreateAdapterRequest,
    UpdateAdapterRequest,
    UpdateAdapterManifestRequest,
    ScraperDashboardResponse,
    ScraperDashboardSummaryResponse,
    ScraperManifestListResponse,
    ScraperManifestResponse,
    ScraperRunHistoryListResponse,
    ScraperRunCancelResponse,
    ScraperRunHistoryResponse,
    ScraperRunLogListResponse,
    ScraperRunLogResponse,
)
from app.integrations.kyrox_core.auth import AuthContext
from app.core.config import get_settings
from app.modules.scraper.core.browser_service import BrowserConfig
from app.modules.scraper.core.playwright_availability import playwright_browser_unavailable_message
from app.modules.scraper.services.adapter_engine_service import AdapterEngineService
from app.modules.scraper.services.adapter_linked_fair_service import AdapterLinkedFairService
from app.modules.scraper.services.scraper_adapter_service import ScraperAdapterService
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.services.scraper_run_log_service import ScraperRunLogService
from app.modules.scraper.services.adapter_instance_resolver import resolve_output_formats
from app.modules.scraper.application.delete_adapter import DeleteAdapterUseCase
from app.modules.scraper.application.adapter_test_run_job_runner import (
    AdapterTestRunJobCommand,
    AdapterTestRunJobRunner,
)
from app.modules.scraper.application.enrichment_run_job_runner import (
    EnrichmentRunJobCommand,
    EnrichmentRunJobRunner,
)
from app.modules.scraper.application.run_adapter_test import (
    AdapterNotRegisteredError,
    DynamicAdapterEngineNotRunnableError,
    RunAdapterTestCommand,
    RunAdapterTestUseCase,
)
from app.modules.scraper.application.run_enrichment import (
    EnrichmentAdapterNotSupportedError,
    RunEnrichmentCommand,
    RunEnrichmentUseCase,
)
from app.modules.scraper.domain.enrichment_adapter import is_customer_contact_enrichment_adapter
from app.modules.scraper.domain.scraper_adapter_exceptions import (
    AdapterEngineNotFoundError,
    AdapterNotFoundError,
    DuplicateAdapterKeyError,
    InvalidAdapterKeyError,
    InvalidAdapterNameError,
)
from app.modules.scraper.domain.adapter_engine import AdapterEngineType
from app.modules.scraper.domain.scraper_run_history import ScraperRunHistory, ScraperRunStatus
from app.modules.scraper.domain.scraper_run_log import ScraperRunLogLevel
from app.modules.scraper.domain.scraper_run_history_filters import ScraperRunHistoryListFilters
from app.modules.scraper.infrastructure.handoff_storage import (
    resolve_handoff_excel_path,
    resolve_handoff_path,
)
from app.modules.scraper.core.scraper_manager import ScraperManager
from app.modules.scraper.services.scraper_dashboard_service import ScraperDashboardService
from app.modules.scraper.services.scraper_run_history_list_builder import build_run_history_list_item
from app.modules.scraper.services.enrichment_run_log_export_service import (
    export_enrichment_run_logs,
    is_supported_export_format,
)
from app.modules.scraper.services.enrichment_run_summary_loader import load_enrichment_summary_for_run
from app.modules.scraper.types.scraper_site import ScraperSiteKey

router = APIRouter(prefix="/scraper", tags=["Adapter Yönetimi"])


def _build_run_history_response(
    row,
    *,
    engine_service: AdapterEngineService,
    run_log_service: ScraperRunLogService | None = None,
) -> ScraperRunHistoryResponse:
    item = build_run_history_list_item(row, engine_service=engine_service)
    enrichment_summary = None
    if run_log_service is not None and is_customer_contact_enrichment_adapter(item["run"].adapter_key):
        enrichment_summary = load_enrichment_summary_for_run(run_log_service, item["run"].id)
    return ScraperRunHistoryResponse.from_list_item(
        {**item, "enrichment_summary": enrichment_summary} if enrichment_summary is not None else item
    )


def _parse_run_status(value: str | None) -> ScraperRunStatus | None:
    if not value:
        return None
    try:
        return ScraperRunStatus(value.strip().lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid run status: {value}",
        ) from exc


def _parse_datetime(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    try:
        if len(text) == 10:
            parsed = datetime.fromisoformat(text)
            if end_of_day:
                parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
            return parsed.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime: {value}",
        ) from exc


def _resolve_engine_keys(
    engine_service: AdapterEngineService,
    engine_type: AdapterEngineType | None,
) -> tuple[str, ...] | None:
    if engine_type is None:
        return None
    keys = tuple(
        engine.engine_key
        for engine in engine_service.list_engines()
        if engine.engine_type == engine_type
    )
    return keys or ("__no_engine_match__",)


def _adapter_http_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, DuplicateAdapterKeyError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, (InvalidAdapterKeyError, InvalidAdapterNameError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, AdapterNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, AdapterEngineNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    raise exc


def _get_org_scoped_run(
    run_history_service: ScraperRunHistoryService,
    run_id: UUID,
    organization_id: UUID,
) -> ScraperRunHistory:
    run = run_history_service.get_run_for_organization(run_id, organization_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scraper run not found: {run_id}",
        )
    return run


@router.get(
    "/engines",
    response_model=AdapterEngineListResponse,
    summary="Adapter engine listesi",
)
def list_adapter_engines(
    auth: Annotated[AuthContext, Depends(require_read_permission)],
    engine_service: Annotated[AdapterEngineService, Depends(get_adapter_engine_service)],
) -> AdapterEngineListResponse:
    _ = auth
    items = [AdapterEngineResponse.from_view(view) for view in engine_service.list_engines()]
    return AdapterEngineListResponse(items=items, total=len(items))


@router.get(
    "/adapters",
    response_model=AdapterListResponse,
    summary="Adapter kayıt listesi",
)
def list_adapters(
    auth: Annotated[AuthContext, Depends(require_read_permission)],
    adapter_service: Annotated[ScraperAdapterService, Depends(get_scraper_adapter_service)],
) -> AdapterListResponse:
    items = [
        AdapterListItemResponse.from_managed_view(view)
        for view in adapter_service.list_adapters(auth.organization_id)
    ]
    return AdapterListResponse(items=items, total=len(items))


@router.post(
    "/adapters",
    response_model=AdapterDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adapter oluştur",
)
def create_adapter(
    body: CreateAdapterRequest,
    auth: Annotated[AuthContext, Depends(require_create_permission)],
    adapter_service: Annotated[ScraperAdapterService, Depends(get_scraper_adapter_service)],
) -> AdapterDetailResponse:
    try:
        view = adapter_service.create_adapter(
            auth.organization_id,
            name=body.name,
            description=body.description,
            engine_key=body.engine_key,
            version=body.version,
            last_verified=body.last_verified,
            supported_sites=body.supported_sites,
            output=body.output.model_dump(exclude_unset=True) if body.output is not None else None,
            browser=body.browser.model_dump(exclude_unset=True) if body.browser is not None else None,
            requested_fields=body.requested_fields,
            adapter_key=body.adapter_key,
            is_active=body.is_active,
        )
    except (DuplicateAdapterKeyError, InvalidAdapterKeyError, InvalidAdapterNameError, AdapterEngineNotFoundError) as exc:
        raise _adapter_http_errors(exc) from exc
    return AdapterDetailResponse.from_managed_view(view)


@router.get(
    "/adapters/{adapter}",
    response_model=AdapterDetailResponse,
    summary="Adapter kayıt detayı",
)
def get_adapter(
    adapter: str,
    auth: Annotated[AuthContext, Depends(require_read_permission)],
    adapter_service: Annotated[ScraperAdapterService, Depends(get_scraper_adapter_service)],
) -> AdapterDetailResponse:
    try:
        view = adapter_service.get_adapter(auth.organization_id, adapter)
    except (AdapterNotFoundError, InvalidAdapterKeyError) as exc:
        raise _adapter_http_errors(exc) from exc
    return AdapterDetailResponse.from_managed_view(view)


@router.patch(
    "/adapters/{adapter}",
    response_model=AdapterDetailResponse,
    summary="Adapter güncelle",
)
def update_adapter(
    adapter: str,
    body: UpdateAdapterRequest,
    auth: Annotated[AuthContext, Depends(require_update_permission)],
    adapter_service: Annotated[ScraperAdapterService, Depends(get_scraper_adapter_service)],
) -> AdapterDetailResponse:
    try:
        view = adapter_service.update_adapter(
            auth.organization_id,
            adapter,
            **body.model_dump(exclude_unset=True),
        )
    except (AdapterNotFoundError, InvalidAdapterKeyError, InvalidAdapterNameError) as exc:
        raise _adapter_http_errors(exc) from exc
    return AdapterDetailResponse.from_managed_view(view)


@router.patch(
    "/adapters/{adapter}/manifest",
    response_model=ScraperManifestResponse,
    summary="Adapter manifest güncelle",
)
def update_adapter_manifest(
    adapter: str,
    body: UpdateAdapterManifestRequest,
    auth: Annotated[AuthContext, Depends(require_update_permission)],
    adapter_service: Annotated[ScraperAdapterService, Depends(get_scraper_adapter_service)],
) -> ScraperManifestResponse:
    payload = body.model_dump(exclude_unset=True)
    if body.output is not None:
        payload["output"] = body.output.model_dump(exclude_unset=True)
    if body.browser is not None:
        payload["browser"] = body.browser.model_dump(exclude_unset=True)
    if body.supports is not None:
        payload["supports"] = body.supports.model_dump(exclude_unset=True)
    try:
        merged = adapter_service.update_adapter_manifest(
            auth.organization_id,
            adapter,
            payload,
        )
    except (AdapterNotFoundError, InvalidAdapterKeyError, InvalidAdapterNameError) as exc:
        raise _adapter_http_errors(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    requested_fields = adapter_service.resolve_requested_fields(auth.organization_id, adapter)
    return ScraperManifestResponse.from_manifest(merged, requested_fields=requested_fields)


@router.post(
    "/adapters/{adapter}/activate",
    response_model=AdapterDetailResponse,
    summary="Adapter aktif et",
)
def activate_adapter(
    adapter: str,
    auth: Annotated[AuthContext, Depends(require_update_permission)],
    adapter_service: Annotated[ScraperAdapterService, Depends(get_scraper_adapter_service)],
) -> AdapterDetailResponse:
    try:
        view = adapter_service.activate_adapter(auth.organization_id, adapter)
    except (AdapterNotFoundError, InvalidAdapterKeyError) as exc:
        raise _adapter_http_errors(exc) from exc
    return AdapterDetailResponse.from_managed_view(view)


@router.post(
    "/adapters/{adapter}/deactivate",
    response_model=AdapterDetailResponse,
    summary="Adapter pasif et",
)
def deactivate_adapter(
    adapter: str,
    auth: Annotated[AuthContext, Depends(require_update_permission)],
    adapter_service: Annotated[ScraperAdapterService, Depends(get_scraper_adapter_service)],
) -> AdapterDetailResponse:
    try:
        view = adapter_service.deactivate_adapter(auth.organization_id, adapter)
    except (AdapterNotFoundError, InvalidAdapterKeyError) as exc:
        raise _adapter_http_errors(exc) from exc
    return AdapterDetailResponse.from_managed_view(view)


@router.get(
    "/adapters/{adapter}/delete-preview",
    response_model=AdapterDeletePreviewResponse,
    summary="Adapter silme önizlemesi",
)
def get_adapter_delete_preview(
    adapter: str,
    auth: Annotated[AuthContext, Depends(require_read_permission)],
    use_case: Annotated[DeleteAdapterUseCase, Depends(get_delete_adapter_use_case)],
) -> AdapterDeletePreviewResponse:
    try:
        preview = use_case.get_delete_preview(auth.organization_id, adapter)
    except (AdapterNotFoundError, InvalidAdapterKeyError) as exc:
        raise _adapter_http_errors(exc) from exc
    return AdapterDeletePreviewResponse(
        adapter_key=preview.adapter_key,
        display_name=preview.display_name,
        linked_fairs_count=preview.linked_fairs_count,
        affected_fairs=list(preview.affected_fairs),
        active_runs_count=preview.active_runs_count,
        active_runs=[
            AdapterDeletePreviewActiveRunResponse(
                id=run.id,
                fair_name=run.fair_name,
                input_url=run.input_url,
                started_at=run.started_at,
            )
            for run in preview.active_runs
        ],
    )


@router.delete(
    "/adapters/{adapter}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Adapter sil",
)
def delete_adapter(
    adapter: str,
    auth: Annotated[AuthContext, Depends(require_delete_permission)],
    db: Annotated[Session, Depends(get_db)],
    use_case: Annotated[DeleteAdapterUseCase, Depends(get_delete_adapter_use_case)],
) -> None:
    try:
        use_case.execute(auth.organization_id, adapter)
    except (AdapterNotFoundError, InvalidAdapterKeyError) as exc:
        raise _adapter_http_errors(exc) from exc
    db.commit()


@router.get(
    "/dashboard",
    response_model=ScraperDashboardResponse,
    summary="Adapter yönetimi dashboard",
)
def get_scraper_dashboard(
    auth: Annotated[AuthContext, Depends(require_read_permission)],
    dashboard_service: Annotated[ScraperDashboardService, Depends(get_default_scraper_dashboard_service)],
) -> ScraperDashboardResponse:
    manifests = dashboard_service.list_manifests()
    adapters = [AdapterListItemResponse.from_manifest(manifest) for manifest in manifests]
    summary = ScraperDashboardSummaryResponse(**dashboard_service.build_summary(auth.organization_id))
    return ScraperDashboardResponse(summary=summary, adapters=adapters)


@router.get(
    "/manifests",
    response_model=ScraperManifestListResponse,
    summary="Adapter listesi",
)
def list_scraper_manifests(
    auth: Annotated[AuthContext, Depends(require_read_permission)],
    manager: Annotated[ScraperManager, Depends(get_default_scraper_manager)],
) -> ScraperManifestListResponse:
    _ = auth
    manifests = manager.list_manifests()
    items = [AdapterListItemResponse.from_manifest(manifest) for manifest in manifests]
    return ScraperManifestListResponse(items=items, total=len(items))


@router.get(
    "/manifests/{adapter}",
    response_model=ScraperManifestResponse,
    summary="Adapter manifest detayı",
)
def get_scraper_manifest(
    adapter: str,
    auth: Annotated[AuthContext, Depends(require_read_permission)],
    adapter_service: Annotated[ScraperAdapterService, Depends(get_scraper_adapter_service)],
) -> ScraperManifestResponse:
    try:
        manifest = adapter_service.get_merged_manifest(auth.organization_id, adapter)
    except (AdapterNotFoundError, InvalidAdapterKeyError) as exc:
        raise _adapter_http_errors(exc) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    requested_fields = adapter_service.resolve_requested_fields(auth.organization_id, adapter)
    return ScraperManifestResponse.from_manifest(manifest, requested_fields=requested_fields)


@router.get(
    "/adapters/{adapter}/fairs",
    response_model=AdapterLinkedFairListResponse,
    summary="Adapter'a bağlı fuarlar",
)
def list_adapter_linked_fairs(
    adapter: str,
    auth: Annotated[AuthContext, Depends(require_read_permission)],
    linked_fair_service: Annotated[AdapterLinkedFairService, Depends(get_adapter_linked_fair_service)],
) -> AdapterLinkedFairListResponse:
    try:
        fairs = linked_fair_service.list_linked_fairs(auth.organization_id, adapter)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    items = [AdapterLinkedFairResponse.from_entity(fair) for fair in fairs]
    return AdapterLinkedFairListResponse(items=items, total=len(items))


@router.post(
    "/adapters/{adapter}/test-run",
    response_model=ScraperRunHistoryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Adapter test çalıştırması başlat",
)
def run_adapter_test(
    adapter: str,
    body: AdapterTestRunRequest,
    background_tasks: BackgroundTasks,
    auth: Annotated[AuthContext, Depends(require_run_permission)],
    db: Annotated[Session, Depends(get_db)],
    use_case: Annotated[RunAdapterTestUseCase, Depends(get_run_adapter_test_use_case)],
    job_runner: Annotated[AdapterTestRunJobRunner, Depends(get_adapter_test_run_job_runner)],
) -> ScraperRunHistoryResponse:
    unavailable = playwright_browser_unavailable_message(BrowserConfig.from_settings(get_settings()))
    if unavailable:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=unavailable)
    try:
        run = use_case.execute(
            RunAdapterTestCommand(
                organization_id=auth.organization_id,
                adapter_key=adapter,
                input_url=body.input_url,
            )
        )
    except (AdapterNotRegisteredError, AdapterEngineNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ValueError, DynamicAdapterEngineNotRunnableError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    output_formats = resolve_output_formats(
        db,
        auth.organization_id,
        run.adapter_key,
        output_json_override=body.output_json,
        output_excel_override=body.output_excel,
    )
    if not output_formats.json_handoff and not output_formats.excel:
        output_formats = replace(output_formats, json_handoff=True)
    background_tasks.add_task(
        run_blocking_background_task,
        job_runner.run_adapter_test,
        AdapterTestRunJobCommand(
            run_id=run.id,
            organization_id=auth.organization_id,
            adapter_key=run.adapter_key,
            input_url=run.input_url or body.input_url.strip(),
            output_json=output_formats.json_handoff,
            output_excel=output_formats.excel,
            max_pages=body.max_pages,
        ),
    )
    return ScraperRunHistoryResponse.from_entity(run)


@router.post(
    "/adapters/{adapter}/enrichment-run",
    response_model=ScraperRunHistoryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Müşteri iletişim zenginleştirme çalıştırması başlat",
)
def run_customer_contact_enrichment(
    adapter: str,
    body: EnrichmentRunRequest,
    background_tasks: BackgroundTasks,
    auth: Annotated[AuthContext, Depends(require_run_permission)],
    db: Annotated[Session, Depends(get_db)],
    use_case: Annotated[RunEnrichmentUseCase, Depends(get_run_enrichment_use_case)],
    job_runner: Annotated[EnrichmentRunJobRunner, Depends(get_enrichment_run_job_runner)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> ScraperRunHistoryResponse:
    if adapter.strip().lower() != ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Enrichment run is only available for {ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT}",
        )
    try:
        run = use_case.execute(
            RunEnrichmentCommand(
                organization_id=auth.organization_id,
                adapter_key=adapter,
                limit=body.limit,
            )
        )
    except EnrichmentAdapterNotSupportedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    access_token = credentials.credentials if credentials is not None else ""
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
        ),
    )
    return ScraperRunHistoryResponse.from_entity(run)


@router.post(
    "/enrichment-state/reset",
    response_model=EnrichmentStateResetResponse,
    summary="Müşteri iletişim zenginleştirme durumunu sıfırla",
)
def reset_customer_enrichment_state(
    body: EnrichmentStateResetRequest,
    auth: Annotated[AuthContext, Depends(require_run_permission)],
    db: Annotated[Session, Depends(get_db)],
) -> EnrichmentStateResetResponse:
    from app.modules.scraper.services.customer_enrichment_state_service import reset_enrichment_states

    if not body.reset_all and not body.customer_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="customer_ids veya reset_all belirtilmelidir",
        )
    deleted = reset_enrichment_states(
        db,
        organization_id=auth.organization_id,
        customer_ids=None if body.reset_all else body.customer_ids,
    )
    db.commit()
    return EnrichmentStateResetResponse(deleted_count=deleted)


@router.get(
    "/runs",
    response_model=ScraperRunHistoryListResponse,
    summary="Adapter çalıştırma geçmişi",
)
def list_scraper_runs(
    auth: Annotated[AuthContext, Depends(require_read_permission)],
    run_history_service: Annotated[ScraperRunHistoryService, Depends(get_scraper_run_history_service)],
    engine_service: Annotated[AdapterEngineService, Depends(get_adapter_engine_service)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    fair_id: UUID | None = None,
    adapter_key: str | None = None,
    adapter_id: UUID | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    engine_type: AdapterEngineType | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    q: str | None = None,
    url: str | None = None,
) -> ScraperRunHistoryListResponse:
    filters = ScraperRunHistoryListFilters(
        organization_id=auth.organization_id,
        adapter_key=adapter_key,
        adapter_id=adapter_id,
        status=_parse_run_status(status_filter),
        engine_keys=_resolve_engine_keys(engine_service, engine_type),
        date_from=_parse_datetime(date_from),
        date_to=_parse_datetime(date_to, end_of_day=True),
        url_query=(url or q or "").strip() or None,
        fair_id=fair_id,
    )
    rows = run_history_service.list_run_rows(limit=limit, offset=offset, filters=filters)
    items = [
        ScraperRunHistoryResponse.from_list_item(
            build_run_history_list_item(row, engine_service=engine_service)
        )
        for row in rows
    ]
    return ScraperRunHistoryListResponse(
        items=items,
        total=run_history_service.count_runs(filters=filters),
    )


@router.get(
    "/runs/{run_id}",
    response_model=ScraperRunHistoryResponse,
    summary="Adapter çalıştırma detayı",
)
def get_scraper_run(
    run_id: UUID,
    auth: Annotated[AuthContext, Depends(require_read_permission)],
    run_history_service: Annotated[ScraperRunHistoryService, Depends(get_scraper_run_history_service)],
    run_log_service: Annotated[ScraperRunLogService, Depends(get_scraper_run_log_service)],
    engine_service: Annotated[AdapterEngineService, Depends(get_adapter_engine_service)],
) -> ScraperRunHistoryResponse:
    row = run_history_service.get_run_row(run_id, organization_id=auth.organization_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scraper run not found: {run_id}",
        )
    return _build_run_history_response(
        row,
        engine_service=engine_service,
        run_log_service=run_log_service,
    )


@router.post(
    "/runs/{run_id}/cancel",
    response_model=ScraperRunCancelResponse,
    summary="Uzun süren adapter çalıştırmasını güvenli durdur",
)
def cancel_scraper_run(
    run_id: UUID,
    auth: Annotated[AuthContext, Depends(require_run_permission)],
    db: Annotated[Session, Depends(get_db)],
    run_history_service: Annotated[ScraperRunHistoryService, Depends(get_scraper_run_history_service)],
    run_log_service: Annotated[ScraperRunLogService, Depends(get_scraper_run_log_service)],
) -> ScraperRunCancelResponse:
    run = _get_org_scoped_run(run_history_service, run_id, auth.organization_id)
    if run.status not in {ScraperRunStatus.RUNNING, ScraperRunStatus.CANCEL_REQUESTED}:
        return ScraperRunCancelResponse(
            job_id=run.id,
            status=run.status,
            cancel_requested_at=run.cancel_requested_at,
            message="İş zaten durdurulmuş veya tamamlanmış.",
        )
    updated = run_history_service.request_cancel(
        run_id,
        organization_id=auth.organization_id,
        requested_by=auth.user_id,
    )
    run_log_service.append_log(
        run_id=run_id,
        level=ScraperRunLogLevel.INFO,
        step="cancel_requested",
        message="İptal isteği alındı. İş güvenli noktada durdurulacak.",
        metadata={
            "cancel_requested_by": str(auth.user_id),
            "cancel_requested_at": (
                updated.cancel_requested_at.isoformat() if updated.cancel_requested_at is not None else None
            ),
        },
    )
    db.commit()
    return ScraperRunCancelResponse(
        job_id=updated.id,
        status=updated.status,
        cancel_requested_at=updated.cancel_requested_at,
        message="İptal isteği alındı. İş güvenli noktada durdurulacak.",
    )


@router.get(
    "/runs/{run_id}/logs",
    response_model=ScraperRunLogListResponse,
    summary="Adapter çalıştırma konsol logları",
)
def list_scraper_run_logs(
    run_id: UUID,
    auth: Annotated[AuthContext, Depends(require_read_permission)],
    run_history_service: Annotated[ScraperRunHistoryService, Depends(get_scraper_run_history_service)],
    run_log_service: Annotated[ScraperRunLogService, Depends(get_scraper_run_log_service)],
    after_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=2000)] = 500,
) -> ScraperRunLogListResponse:
    run = _get_org_scoped_run(run_history_service, run_id, auth.organization_id)
    logs = run_log_service.list_logs(run_id, after_id=after_id, limit=limit)
    items = [ScraperRunLogResponse.from_entity(log) for log in logs]
    json_path = resolve_handoff_path(run_id)
    excel_path = resolve_handoff_excel_path(run_id)
    outputs_ready = run.status == ScraperRunStatus.COMPLETED

    def _artifact_available(default_path: Path, stored_path: str | None) -> bool:
        if default_path.is_file():
            return True
        if stored_path:
            return Path(stored_path).is_file()
        return False

    return ScraperRunLogListResponse(
        items=items,
        total=run_log_service.count_logs(run_id),
        run_status=run.status,
        total_rows=run.total_rows,
        output_json_available=outputs_ready and _artifact_available(json_path, run.output_json_path),
        output_excel_available=outputs_ready and _artifact_available(excel_path, run.output_excel_path),
    )


@router.get(
    "/runs/{run_id}/logs/export",
    summary="Zenginleştirme çalışması log dışa aktarma",
)
def export_scraper_run_logs(
    run_id: UUID,
    auth: Annotated[AuthContext, Depends(require_read_permission)],
    run_history_service: Annotated[ScraperRunHistoryService, Depends(get_scraper_run_history_service)],
    run_log_service: Annotated[ScraperRunLogService, Depends(get_scraper_run_log_service)],
    format: Annotated[str, Query(alias="format")],
) -> Response:
    if not is_supported_export_format(format):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Desteklenmeyen format.",
        )
    run = _get_org_scoped_run(run_history_service, run_id, auth.organization_id)
    if not is_customer_contact_enrichment_adapter(run.adapter_key):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scraper run not found: {run_id}",
        )
    try:
        content, filename, media_type = export_enrichment_run_logs(
            run=run,
            run_log_service=run_log_service,
            export_format=format,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/runs/{run_id}/output/json",
    summary="Adapter test JSON çıktısı",
)
def download_scraper_run_json(
    run_id: UUID,
    auth: Annotated[AuthContext, Depends(require_download_permission)],
    run_history_service: Annotated[ScraperRunHistoryService, Depends(get_scraper_run_history_service)],
) -> FileResponse:
    run = _get_org_scoped_run(run_history_service, run_id, auth.organization_id)
    if run.status != ScraperRunStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test çıktısı henüz hazır değil.",
        )
    path = resolve_handoff_path(run_id)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="JSON çıktı dosyası bulunamadı.",
        )
    return FileResponse(
        path=path,
        media_type="application/json",
        filename=f"{run_id}.json",
    )


@router.get(
    "/runs/{run_id}/output/excel",
    summary="Adapter test Excel çıktısı",
)
def download_scraper_run_excel(
    run_id: UUID,
    auth: Annotated[AuthContext, Depends(require_download_permission)],
    run_history_service: Annotated[ScraperRunHistoryService, Depends(get_scraper_run_history_service)],
) -> FileResponse:
    run = _get_org_scoped_run(run_history_service, run_id, auth.organization_id)
    if run.status != ScraperRunStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test çıktısı henüz hazır değil.",
        )
    path = resolve_handoff_excel_path(run_id)
    if not path.is_file() and run.output_excel_path:
        candidate = Path(run.output_excel_path)
        if candidate.is_file():
            path = candidate
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Excel çıktı dosyası bulunamadı.",
        )
    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"{run_id}.xlsx",
    )

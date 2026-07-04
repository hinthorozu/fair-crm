"""HTTP routes for Adapter Yönetimi (adapter manifest discovery and dashboard)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.shared.background_jobs import run_blocking_background_task

from app.modules.scraper.api.dependencies import (
    get_adapter_linked_fair_service,
    get_adapter_test_run_job_runner,
    get_auth_context,
    get_default_scraper_dashboard_service,
    get_default_scraper_manager,
    get_run_adapter_test_use_case,
    get_scraper_adapter_service,
    get_scraper_run_history_service,
    get_scraper_run_log_service,
)
from app.modules.scraper.api.schemas import (
    AdapterDetailResponse,
    AdapterLinkedFairListResponse,
    AdapterLinkedFairResponse,
    AdapterListItemResponse,
    AdapterListResponse,
    AdapterTestRunRequest,
    CreateAdapterRequest,
    UpdateAdapterRequest,
    UpdateAdapterManifestRequest,
    ScraperDashboardResponse,
    ScraperDashboardSummaryResponse,
    ScraperManifestListResponse,
    ScraperManifestResponse,
    ScraperRunHistoryListResponse,
    ScraperRunHistoryResponse,
    ScraperRunLogListResponse,
    ScraperRunLogResponse,
)
from app.integrations.kyrox_core.auth import AuthContext
from app.core.config import get_settings
from app.modules.scraper.core.browser_service import BrowserConfig
from app.modules.scraper.core.playwright_availability import playwright_browser_unavailable_message
from app.modules.scraper.services.adapter_linked_fair_service import AdapterLinkedFairService
from app.modules.scraper.services.scraper_adapter_service import ScraperAdapterService
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.services.scraper_run_log_service import ScraperRunLogService
from app.modules.scraper.application.adapter_test_run_job_runner import (
    AdapterTestRunJobCommand,
    AdapterTestRunJobRunner,
)
from app.modules.scraper.application.run_adapter_test import (
    AdapterNotRegisteredError,
    RunAdapterTestCommand,
    RunAdapterTestUseCase,
)
from app.modules.scraper.domain.scraper_adapter_exceptions import (
    AdapterNotFoundError,
    DuplicateAdapterKeyError,
    InvalidAdapterKeyError,
    InvalidAdapterNameError,
)
from app.modules.scraper.domain.scraper_run_history import ScraperRunStatus
from app.modules.scraper.infrastructure.handoff_storage import (
    resolve_handoff_excel_path,
    resolve_handoff_path,
)
from app.modules.scraper.core.scraper_manager import ScraperManager
from app.modules.scraper.services.scraper_dashboard_service import ScraperDashboardService

router = APIRouter(prefix="/scraper", tags=["Adapter Yönetimi"])


def _adapter_http_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, DuplicateAdapterKeyError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, (InvalidAdapterKeyError, InvalidAdapterNameError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, AdapterNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    raise exc


@router.get(
    "/adapters",
    response_model=AdapterListResponse,
    summary="Adapter kayıt listesi",
)
def list_adapters(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
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
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    adapter_service: Annotated[ScraperAdapterService, Depends(get_scraper_adapter_service)],
) -> AdapterDetailResponse:
    try:
        view = adapter_service.create_adapter(
            auth.organization_id,
            adapter_key=body.adapter_key,
            name=body.name,
            description=body.description,
            status=body.status,
            version=body.version,
            manifest=body.manifest,
            is_active=body.is_active,
        )
    except (DuplicateAdapterKeyError, InvalidAdapterKeyError, InvalidAdapterNameError) as exc:
        raise _adapter_http_errors(exc) from exc
    return AdapterDetailResponse.from_managed_view(view)


@router.get(
    "/adapters/{adapter}",
    response_model=AdapterDetailResponse,
    summary="Adapter kayıt detayı",
)
def get_adapter(
    adapter: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
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
    auth: Annotated[AuthContext, Depends(get_auth_context)],
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
    auth: Annotated[AuthContext, Depends(get_auth_context)],
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
    return ScraperManifestResponse.from_manifest(merged)


@router.post(
    "/adapters/{adapter}/activate",
    response_model=AdapterDetailResponse,
    summary="Adapter aktif et",
)
def activate_adapter(
    adapter: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
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
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    adapter_service: Annotated[ScraperAdapterService, Depends(get_scraper_adapter_service)],
) -> AdapterDetailResponse:
    try:
        view = adapter_service.deactivate_adapter(auth.organization_id, adapter)
    except (AdapterNotFoundError, InvalidAdapterKeyError) as exc:
        raise _adapter_http_errors(exc) from exc
    return AdapterDetailResponse.from_managed_view(view)


@router.get(
    "/dashboard",
    response_model=ScraperDashboardResponse,
    summary="Adapter yönetimi dashboard",
)
def get_scraper_dashboard(
    dashboard_service: Annotated[ScraperDashboardService, Depends(get_default_scraper_dashboard_service)],
) -> ScraperDashboardResponse:
    manifests = dashboard_service.list_manifests()
    adapters = [AdapterListItemResponse.from_manifest(manifest) for manifest in manifests]
    summary = ScraperDashboardSummaryResponse(**dashboard_service.build_summary())
    return ScraperDashboardResponse(summary=summary, adapters=adapters)


@router.get(
    "/manifests",
    response_model=ScraperManifestListResponse,
    summary="Adapter listesi",
)
def list_scraper_manifests(
    manager: Annotated[ScraperManager, Depends(get_default_scraper_manager)],
) -> ScraperManifestListResponse:
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
    auth: Annotated[AuthContext, Depends(get_auth_context)],
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
    return ScraperManifestResponse.from_manifest(manifest)


@router.get(
    "/adapters/{adapter}/fairs",
    response_model=AdapterLinkedFairListResponse,
    summary="Adapter'a bağlı fuarlar",
)
def list_adapter_linked_fairs(
    adapter: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
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
    auth: Annotated[AuthContext, Depends(get_auth_context)],
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
    except AdapterNotRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    background_tasks.add_task(
        run_blocking_background_task,
        job_runner.run_adapter_test,
        AdapterTestRunJobCommand(
            run_id=run.id,
            organization_id=auth.organization_id,
            adapter_key=run.adapter_key,
            input_url=run.input_url or body.input_url.strip(),
        ),
    )
    return ScraperRunHistoryResponse.from_entity(run)


@router.get(
    "/runs",
    response_model=ScraperRunHistoryListResponse,
    summary="Adapter çalıştırma geçmişi",
)
def list_scraper_runs(
    run_history_service: Annotated[ScraperRunHistoryService, Depends(get_scraper_run_history_service)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    fair_id: UUID | None = None,
) -> ScraperRunHistoryListResponse:
    runs = run_history_service.list_runs(limit=limit, offset=offset, fair_id=fair_id)
    items = [ScraperRunHistoryResponse.from_entity(run) for run in runs]
    return ScraperRunHistoryListResponse(
        items=items,
        total=run_history_service.count_runs(fair_id=fair_id),
    )


@router.get(
    "/runs/{run_id}",
    response_model=ScraperRunHistoryResponse,
    summary="Adapter çalıştırma detayı",
)
def get_scraper_run(
    run_id: UUID,
    run_history_service: Annotated[ScraperRunHistoryService, Depends(get_scraper_run_history_service)],
) -> ScraperRunHistoryResponse:
    run = run_history_service.get_run(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scraper run not found: {run_id}",
        )
    return ScraperRunHistoryResponse.from_entity(run)


@router.get(
    "/runs/{run_id}/logs",
    response_model=ScraperRunLogListResponse,
    summary="Adapter çalıştırma konsol logları",
)
def list_scraper_run_logs(
    run_id: UUID,
    run_history_service: Annotated[ScraperRunHistoryService, Depends(get_scraper_run_history_service)],
    run_log_service: Annotated[ScraperRunLogService, Depends(get_scraper_run_log_service)],
    after_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=2000)] = 500,
) -> ScraperRunLogListResponse:
    run = run_history_service.get_run(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scraper run not found: {run_id}",
        )
    logs = run_log_service.list_logs(run_id, after_id=after_id, limit=limit)
    items = [ScraperRunLogResponse.from_entity(log) for log in logs]
    json_path = resolve_handoff_path(run_id)
    excel_path = resolve_handoff_excel_path(run_id)
    outputs_ready = run.status == ScraperRunStatus.COMPLETED
    return ScraperRunLogListResponse(
        items=items,
        total=run_log_service.count_logs(run_id),
        run_status=run.status,
        total_rows=run.total_rows,
        output_json_available=outputs_ready and json_path.is_file(),
        output_excel_available=outputs_ready and excel_path.is_file(),
    )


@router.get(
    "/runs/{run_id}/output/json",
    summary="Adapter test JSON çıktısı",
)
def download_scraper_run_json(
    run_id: UUID,
    run_history_service: Annotated[ScraperRunHistoryService, Depends(get_scraper_run_history_service)],
) -> FileResponse:
    run = run_history_service.get_run(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scraper run not found: {run_id}",
        )
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
    run_history_service: Annotated[ScraperRunHistoryService, Depends(get_scraper_run_history_service)],
) -> FileResponse:
    run = run_history_service.get_run(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scraper run not found: {run_id}",
        )
    if run.status != ScraperRunStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test çıktısı henüz hazır değil.",
        )
    path = resolve_handoff_excel_path(run_id)
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

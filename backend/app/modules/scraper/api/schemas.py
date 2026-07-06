"""API schemas for adapter management and manifest endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.scraper.domain.adapter_engine import AdapterEngineType
from app.modules.scraper.domain.scraper_run_history import ScraperRunHistory, ScraperRunStatus
from app.modules.scraper.domain.scraper_run_source import ScraperRunSource
from app.modules.scraper.domain.scraper_run_log import ScraperRunLog, ScraperRunLogLevel
from app.modules.scraper.domain.adapter_linked_fair import AdapterLinkedFair
from app.modules.scraper.manifests.scraper_manifest import ScraperManifest
from app.modules.scraper.services.scraper_dashboard_service import (
    build_adapter_features,
    resolve_actions_available,
)
from app.modules.scraper.services.single_customer_enrichment_service import (
    CustomerContactEnrichmentStateView,
)

if TYPE_CHECKING:
    from app.modules.scraper.services.adapter_engine_service import AdapterEngineView
    from app.modules.scraper.services.scraper_adapter_service import ManagedAdapterView


class ScraperSupportsResponse(BaseModel):
    list_scraping: bool
    detail_scraping: bool
    pagination: bool
    website: bool
    email: bool
    phone: bool
    address: bool
    category: bool
    description: bool


class ScraperOutputResponse(BaseModel):
    json_handoff: bool
    excel: bool


class ScraperBrowserResponse(BaseModel):
    requires_js: bool
    requires_playwright: bool


class ScraperManifestResponse(BaseModel):
    adapter_key: str
    display_name: str
    version: str
    supported_sites: list[str]
    supports: ScraperSupportsResponse
    output: ScraperOutputResponse
    browser: ScraperBrowserResponse
    author: str
    notes: str
    scraper_version: str
    target_site_version: str
    last_verified: str | None = None
    engine_type: AdapterEngineType = AdapterEngineType.STATIC
    requested_fields: list[str] = Field(default_factory=list)

    @classmethod
    def from_manifest(
        cls,
        manifest: ScraperManifest,
        *,
        requested_fields: list[str] | None = None,
    ) -> ScraperManifestResponse:
        payload = manifest.to_dict()
        payload.pop("status", None)
        if requested_fields is not None:
            payload["requested_fields"] = requested_fields
        return cls(**payload)


class AdapterEngineResponse(BaseModel):
    engine_key: str
    display_name: str
    engine_type: AdapterEngineType
    version: str
    supported_sites: list[str] = Field(default_factory=list)
    features: list[AdapterFeatureResponse] = Field(default_factory=list)
    actions_available: list[str] = Field(default_factory=list)
    is_runnable: bool = True

    @classmethod
    def from_view(cls, view: "AdapterEngineView") -> AdapterEngineResponse:
        return cls(
            engine_key=view.engine_key,
            display_name=view.display_name,
            engine_type=view.engine_type,
            version=view.version,
            supported_sites=list(view.supported_sites),
            features=[AdapterFeatureResponse(**feature) for feature in view.features],
            actions_available=view.actions_available,
            is_runnable=view.is_runnable,
        )


class AdapterEngineListResponse(BaseModel):
    items: list[AdapterEngineResponse] = Field(default_factory=list)
    total: int


class AdapterFeatureResponse(BaseModel):
    key: str
    label: str
    enabled: bool


class AdapterListItemResponse(BaseModel):
    adapter_key: str
    engine_key: str
    engine_type: AdapterEngineType
    display_name: str
    version: str
    features: list[AdapterFeatureResponse] = Field(default_factory=list)
    last_verified: str | None = None
    actions_available: list[str] = Field(default_factory=list)
    id: UUID | None = None
    description: str | None = None
    is_active: bool = True
    is_registered: bool = False

    @classmethod
    def from_manifest(cls, manifest: ScraperManifest) -> AdapterListItemResponse:
        return cls(
            adapter_key=manifest.adapter_key,
            engine_key=manifest.adapter_key,
            engine_type=manifest.engine_type,
            display_name=manifest.display_name,
            version=manifest.version,
            features=[AdapterFeatureResponse(**feature) for feature in build_adapter_features(manifest)],
            last_verified=manifest.last_verified,
            actions_available=resolve_actions_available(manifest),
            is_registered=True,
        )

    @classmethod
    def from_managed_view(cls, view: "ManagedAdapterView") -> AdapterListItemResponse:
        return cls(
            id=view.id,
            adapter_key=view.adapter_key,
            engine_key=view.engine_key,
            engine_type=AdapterEngineType(view.engine_type),
            display_name=view.display_name,
            description=view.description,
            version=view.version,
            features=[AdapterFeatureResponse(**feature) for feature in view.features],
            last_verified=view.last_verified,
            actions_available=view.actions_available,
            is_active=view.is_active,
            is_registered=view.is_registered,
        )


class ScraperManifestListResponse(BaseModel):
    items: list[AdapterListItemResponse] = Field(default_factory=list)
    total: int


class ScraperDashboardSummaryResponse(BaseModel):
    total_adapters: int
    last_run_adapter: str | None = None
    failed_scraper_count: int = 0


class ScraperDashboardResponse(BaseModel):
    summary: ScraperDashboardSummaryResponse
    adapters: list[AdapterListItemResponse] = Field(default_factory=list)


class ScraperRunHistoryResponse(BaseModel):
    id: UUID
    adapter_key: str
    status: ScraperRunStatus
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None
    organization_id: UUID | None = None
    fair_id: UUID | None = None
    input_url: str | None = None
    fair_name: str | None = None
    fair_year: int | None = None
    total_rows: int
    website_count: int
    email_count: int
    phone_count: int
    instagram_count: int
    linkedin_count: int
    facebook_count: int
    youtube_count: int
    x_count: int
    error_message: str | None = None
    output_json_path: str | None = None
    output_excel_path: str | None = None
    adapter_name: str | None = None
    engine_key: str | None = None
    engine_type: AdapterEngineType | None = None
    output_json_available: bool = False
    output_excel_available: bool = False
    json_download_url: str | None = None
    json_view_url: str | None = None
    excel_download_url: str | None = None
    excel_view_url: str | None = None
    run_source: ScraperRunSource = ScraperRunSource.MANUAL_TEST
    import_batch_id: UUID | None = None
    import_batch_url: str | None = None
    enrichment_summary: dict[str, Any] | None = None
    cancel_requested_by: UUID | None = None
    cancel_requested_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    progress_current: int | None = None
    progress_total: int | None = None

    @classmethod
    def from_entity(cls, run: ScraperRunHistory, **extra: Any) -> ScraperRunHistoryResponse:
        import_batch_url = None
        if run.import_batch_id is not None:
            import_batch_url = f"/data-integration/imports/continue/{run.import_batch_id}"
        return cls(
            id=run.id,
            adapter_key=run.adapter_key,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            duration_ms=run.duration_ms,
            organization_id=run.organization_id,
            fair_id=run.fair_id,
            input_url=run.input_url,
            fair_name=run.fair_name,
            fair_year=run.fair_year,
            total_rows=run.total_rows,
            website_count=run.website_count,
            email_count=run.email_count,
            phone_count=run.phone_count,
            instagram_count=run.instagram_count,
            linkedin_count=run.linkedin_count,
            facebook_count=run.facebook_count,
            youtube_count=run.youtube_count,
            x_count=run.x_count,
            error_message=run.error_message,
            output_json_path=run.output_json_path,
            output_excel_path=run.output_excel_path,
            run_source=run.run_source,
            import_batch_id=run.import_batch_id,
            import_batch_url=import_batch_url,
            enrichment_summary=extra.get("enrichment_summary"),
            cancel_requested_by=run.cancel_requested_by,
            cancel_requested_at=run.cancel_requested_at,
            last_heartbeat_at=run.last_heartbeat_at,
            progress_current=run.progress_current,
            progress_total=run.progress_total,
            **{k: v for k, v in extra.items() if k != "enrichment_summary"},
        )

    @classmethod
    def from_list_item(cls, item: dict[str, Any]) -> ScraperRunHistoryResponse:
        run = item["run"]
        return cls.from_entity(
            run,
            adapter_name=item.get("adapter_name"),
            engine_key=item.get("engine_key"),
            engine_type=item.get("engine_type"),
            output_json_available=item.get("output_json_available", False),
            output_excel_available=item.get("output_excel_available", False),
            json_download_url=item.get("json_download_url"),
            json_view_url=item.get("json_view_url"),
            excel_download_url=item.get("excel_download_url"),
            excel_view_url=item.get("excel_view_url"),
            enrichment_summary=item.get("enrichment_summary"),
        )


class ScraperRunCancelResponse(BaseModel):
    job_id: UUID
    status: ScraperRunStatus
    cancel_requested_at: datetime | None = None
    message: str


class ScraperRunHistoryListResponse(BaseModel):
    items: list[ScraperRunHistoryResponse] = Field(default_factory=list)
    total: int


class ScraperRunLogResponse(BaseModel):
    id: UUID
    run_id: UUID
    level: ScraperRunLogLevel
    step: str
    message: str
    created_at: datetime
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_entity(cls, log: ScraperRunLog) -> ScraperRunLogResponse:
        return cls(
            id=log.id,
            run_id=log.run_id,
            level=log.level,
            step=log.step,
            message=log.message,
            created_at=log.created_at,
            metadata=log.metadata,
        )


class ScraperRunLogListResponse(BaseModel):
    items: list[ScraperRunLogResponse] = Field(default_factory=list)
    total: int
    run_status: ScraperRunStatus
    total_rows: int = 0
    output_json_available: bool = False
    output_excel_available: bool = False


class AdapterTestRunRequest(BaseModel):
    input_url: str = Field(min_length=1, max_length=2048)
    output_json: bool | None = None
    output_excel: bool | None = None
    max_pages: int | None = Field(default=None, ge=1)


class EnrichmentRunRequest(BaseModel):
    limit: int | None = Field(default=50, ge=1, le=500)
    requested_fields: list[str] | None = None
    dry_run: bool = False
    max_pages: int | None = Field(default=10, ge=1, le=10)


class EnrichmentStateResetRequest(BaseModel):
    customer_ids: list[UUID] | None = None
    reset_all: bool = False


class EnrichmentStateResetResponse(BaseModel):
    deleted_count: int


class CustomerContactEnrichmentRunRequest(BaseModel):
    dry_run: bool = False
    requested_fields: list[str] | None = None
    max_pages: int | None = Field(default=10, ge=1, le=10)


class CustomerContactEnrichmentStateResponse(BaseModel):
    customer_id: UUID
    status: str
    last_email_scan_at: datetime | None = None
    last_email_found: str | None = None
    last_source_url: str | None = None
    last_error: str | None = None
    retry_after: datetime | None = None
    last_enrichment_run_id: UUID | None = None
    import_batch_id: UUID | None = None
    can_run: bool
    block_code: str | None = None
    block_message: str | None = None
    website: str | None = None
    has_crm_email: bool = False
    recent_logs: list[ScraperRunLogResponse] = Field(default_factory=list)

    @classmethod
    def from_view(
        cls,
        view: CustomerContactEnrichmentStateView,
        *,
        recent_logs: list[ScraperRunLog] | None = None,
    ) -> CustomerContactEnrichmentStateResponse:
        return cls(
            customer_id=view.customer_id,
            status=view.status,
            last_email_scan_at=view.last_email_scan_at,
            last_email_found=view.last_email_found,
            last_source_url=view.last_source_url,
            last_error=view.last_error,
            retry_after=view.retry_after,
            last_enrichment_run_id=view.last_enrichment_run_id,
            import_batch_id=view.import_batch_id,
            can_run=view.can_run,
            block_code=view.block_code,
            block_message=view.block_message,
            website=view.website,
            has_crm_email=view.has_crm_email,
            recent_logs=[
                ScraperRunLogResponse.from_entity(log) for log in (recent_logs or [])
            ],
        )


class AdapterLinkedFairResponse(BaseModel):
    id: UUID | None = None
    name: str
    venue: str | None = None
    city: str | None = None
    status: str | None = None
    source_url: str | None = None
    last_import_at: datetime | None = None

    @classmethod
    def from_entity(cls, fair: AdapterLinkedFair) -> AdapterLinkedFairResponse:
        return cls(
            id=fair.id,
            name=fair.name,
            venue=fair.venue,
            city=fair.city,
            status=fair.status,
            source_url=fair.source_url,
            last_import_at=fair.last_import_at,
        )


class AdapterLinkedFairListResponse(BaseModel):
    items: list[AdapterLinkedFairResponse] = Field(default_factory=list)
    total: int


class CreateAdapterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    engine_key: str | None = Field(default=None, max_length=100)
    version: str | None = Field(default=None, max_length=50)
    last_verified: str | None = Field(default=None, max_length=32)
    supported_sites: list[str] | str | None = None
    output: ScraperOutputUpdateRequest | None = None
    browser: ScraperBrowserUpdateRequest | None = None
    requested_fields: list[str] | None = None
    adapter_key: str | None = Field(default=None, max_length=100)
    is_active: bool = True


class UpdateAdapterRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    version: str | None = Field(default=None, max_length=50)
    manifest: dict[str, Any] | None = None
    is_active: bool | None = None


class ScraperOutputUpdateRequest(BaseModel):
    json_handoff: bool | None = None
    excel: bool | None = None


class ScraperBrowserUpdateRequest(BaseModel):
    requires_js: bool | None = None
    requires_playwright: bool | None = None


class ScraperSupportsUpdateRequest(BaseModel):
    list_scraping: bool | None = None
    detail_scraping: bool | None = None
    pagination: bool | None = None
    website: bool | None = None
    email: bool | None = None
    phone: bool | None = None
    address: bool | None = None
    category: bool | None = None
    description: bool | None = None


class UpdateAdapterManifestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    version: str | None = Field(default=None, max_length=50)
    last_verified: str | None = Field(default=None, max_length=32)
    supported_sites: list[str] | str | None = None
    notes: str | None = Field(default=None, max_length=5000)
    output: ScraperOutputUpdateRequest | None = None
    browser: ScraperBrowserUpdateRequest | None = None
    supports: ScraperSupportsUpdateRequest | None = None
    requested_fields: list[str] | None = None


class AdapterDetailResponse(BaseModel):
    id: UUID | None = None
    adapter_key: str
    engine_key: str
    engine_type: AdapterEngineType
    name: str
    description: str | None = None
    version: str
    manifest: dict[str, Any] | None = None
    is_active: bool = True
    is_registered: bool = False
    last_verified: str | None = None
    last_verified_at: datetime | None = None
    features: list[AdapterFeatureResponse] = Field(default_factory=list)
    actions_available: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_managed_view(cls, view: "ManagedAdapterView") -> AdapterDetailResponse:
        return cls(
            id=view.id,
            adapter_key=view.adapter_key,
            engine_key=view.engine_key,
            engine_type=AdapterEngineType(view.engine_type),
            name=view.display_name,
            description=view.description,
            version=view.version,
            manifest=view.manifest,
            is_active=view.is_active,
            is_registered=view.is_registered,
            last_verified=view.last_verified,
            last_verified_at=view.last_verified_at,
            features=[AdapterFeatureResponse(**feature) for feature in view.features],
            actions_available=view.actions_available,
            created_at=view.created_at,
            updated_at=view.updated_at,
        )


class AdapterDeletePreviewActiveRunResponse(BaseModel):
    id: UUID
    fair_name: str | None = None
    input_url: str | None = None
    started_at: datetime


class AdapterDeletePreviewResponse(BaseModel):
    adapter_key: str
    display_name: str
    linked_fairs_count: int
    affected_fairs: list[str] = Field(default_factory=list)
    active_runs_count: int
    active_runs: list[AdapterDeletePreviewActiveRunResponse] = Field(default_factory=list)


class AdapterListResponse(BaseModel):
    items: list[AdapterListItemResponse] = Field(default_factory=list)
    total: int

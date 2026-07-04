"""API schemas for adapter management and manifest endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.scraper.domain.scraper_run_history import ScraperRunHistory, ScraperRunStatus
from app.modules.scraper.domain.scraper_run_log import ScraperRunLog, ScraperRunLogLevel
from app.modules.scraper.domain.adapter_linked_fair import AdapterLinkedFair
from app.modules.scraper.manifests.scraper_manifest import ScraperManifest, ScraperStatus
from app.modules.scraper.services.scraper_dashboard_service import (
    build_adapter_features,
    resolve_actions_available,
)

if TYPE_CHECKING:
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
    status: str
    author: str
    notes: str
    scraper_version: str
    target_site_version: str
    last_verified: str | None = None

    @classmethod
    def from_manifest(cls, manifest: ScraperManifest) -> ScraperManifestResponse:
        return cls(**manifest.to_dict())


class AdapterFeatureResponse(BaseModel):
    key: str
    label: str
    enabled: bool


class AdapterListItemResponse(BaseModel):
    adapter_key: str
    display_name: str
    status: str
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
            display_name=manifest.display_name,
            status=manifest.status.value,
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
            display_name=view.display_name,
            description=view.description,
            status=view.status,
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
    stable_count: int
    experimental_count: int
    deprecated_count: int
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

    @classmethod
    def from_entity(cls, run: ScraperRunHistory) -> ScraperRunHistoryResponse:
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
        )


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
    adapter_key: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    status: ScraperStatus = ScraperStatus.EXPERIMENTAL
    version: str | None = Field(default=None, max_length=50)
    manifest: dict[str, Any] | None = None
    is_active: bool = True


class UpdateAdapterRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    status: ScraperStatus | None = None
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
    status: ScraperStatus | None = None
    version: str | None = Field(default=None, max_length=50)
    last_verified: str | None = Field(default=None, max_length=32)
    supported_sites: list[str] | str | None = None
    notes: str | None = Field(default=None, max_length=5000)
    output: ScraperOutputUpdateRequest | None = None
    browser: ScraperBrowserUpdateRequest | None = None
    supports: ScraperSupportsUpdateRequest | None = None


class AdapterDetailResponse(BaseModel):
    id: UUID | None = None
    adapter_key: str
    name: str
    description: str | None = None
    status: str
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
            name=view.display_name,
            description=view.description,
            status=view.status,
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


class AdapterListResponse(BaseModel):
    items: list[AdapterListItemResponse] = Field(default_factory=list)
    total: int

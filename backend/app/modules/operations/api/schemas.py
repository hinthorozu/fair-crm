from typing import Any, Literal, Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.list_response import StandardListResponse

OperationTypeField = Literal[
    "scraper",
    "email",
    "bulk_email",
    "enrichment",
    "duplicate_check",
    "data_cleanup",
    "whatsapp",
    "manual_task",
    "reminder",
]

OperationStatusField = Literal[
    "draft",
    "ready",
    "active",
    "completed",
    "cancelled",
    "archived",
]

SourceKindField = Literal[
    "fair",
    "import",
    "segment",
    "manual_selection",
    "customer",
    "none",
]

PriorityField = Literal["low", "normal", "high", "urgent"]


class CreateOperationRequest(BaseModel):
    operation_type: OperationTypeField
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=10000)
    source_kind: SourceKindField = "none"
    source_ids: list[UUID] = Field(default_factory=list)
    source_config: dict[str, Any] = Field(default_factory=dict)
    type_config: dict[str, Any] = Field(default_factory=dict)
    run_settings: dict[str, Any] = Field(default_factory=dict)
    priority: PriorityField = "normal"
    status: OperationStatusField = "draft"
    start_immediately: bool = False


class OperationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    operation_id: UUID
    status: str
    progress: float
    total_items: int
    processed_items: int
    succeeded_items: int
    failed_items: int
    attempt: int
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_code: Optional[str]
    error_message: Optional[str]
    error_details: dict[str, Any]
    core_job_id: Optional[UUID]
    triggered_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


class RelatedResourceResponse(BaseModel):
    type: str
    id: UUID


class OperationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    operation_type: str
    title: str
    description: Optional[str]
    status: str
    source_kind: str
    source_ids: list[UUID] = Field(default_factory=list)
    source_config: dict[str, Any]
    type_config: dict[str, Any]
    run_settings: dict[str, Any]
    priority: str
    latest_run_id: Optional[UUID]
    related_todo_id: Optional[UUID] = None
    related_resource: Optional[RelatedResourceResponse] = None
    created_by: UUID
    updated_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    capabilities: dict[str, bool] = Field(default_factory=dict)
    latest_run: Optional[OperationRunResponse] = None


class OperationDetailResponse(BaseModel):
    operation: OperationResponse
    runs: list[OperationRunResponse]


class OperationListResponse(StandardListResponse[OperationResponse]):
    pass


class OperationRunListResponse(StandardListResponse[OperationRunResponse]):
    pass


class WizardStepResponse(BaseModel):
    id: str
    required: bool
    order: int


class OperationTypeMetadataResponse(BaseModel):
    type: str
    label_key: str
    description_key: str
    supported_sources: list[str]
    default_source: str
    capabilities: dict[str, bool]
    wizard_steps: list[WizardStepResponse]
    type_config_schema: dict[str, Any]
    run_settings_schema: dict[str, Any]
    available_in_wizard: bool
    handler_registered: bool


class WizardMetadataResponse(BaseModel):
    types: list[OperationTypeMetadataResponse]
    source_kinds: list[str]
    capabilities_keys: list[str]


class OperationTypeCatalogItemResponse(BaseModel):
    key: str
    name: str
    is_active: bool
    sort_order: int
    supports_pause: bool
    supports_resume: bool
    supports_retry: bool
    supports_schedule: bool
    supports_items: bool
    updated_at: datetime


class OperationTypeCatalogListResponse(BaseModel):
    items: list[OperationTypeCatalogItemResponse]


class UpdateOperationTypeCapabilitiesRequest(BaseModel):
    supports_pause: bool
    supports_resume: bool
    supports_retry: bool
    supports_schedule: bool
    supports_items: bool
    is_active: bool


class ErrorResponse(BaseModel):
    detail: str

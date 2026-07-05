from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.schemas.list_response import StandardListResponse
from app.modules.imports.domain.value_objects import ImportBatchStatus, ImportDecision, ImportRowStatus, ImportSourceType, ExcelHeaderMode


class ImportBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    fair_id: Optional[UUID] = None
    source_type: ImportSourceType = ImportSourceType.EXCEL
    file_name: str
    status: ImportBatchStatus
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    created_rows: int
    updated_rows: int
    skipped_rows: int
    created_participations: int = 0
    updated_participations: int = 0
    ready_to_create: int = 0
    ready_to_update: int = 0
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    selected_sheet_name: Optional[str] = None
    available_sheets: list[str] = Field(default_factory=list)
    header_mode: Optional[ExcelHeaderMode] = None
    has_header_row: Optional[bool] = None
    header_row_index: Optional[int] = None
    column_mapping_json: Optional[dict[str, Any]] = None


class MergeFieldPreviewResponse(BaseModel):
    field_key: str
    label: str
    crm_value: Optional[str] = None
    import_value: Optional[str] = None
    result_value: Optional[str] = None
    outcome: str
    outcome_label: str


class MergeEntityGroupResponse(BaseModel):
    entity: str
    entity_label: str
    fields: list[MergeFieldPreviewResponse]


class MergePreviewResponse(BaseModel):
    groups: list[MergeEntityGroupResponse]
    summary_lines: list[str]
    contact_warnings: list[str] = Field(default_factory=list)


class ImportRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    batch_id: UUID
    row_number: int
    raw_data_json: dict[str, Any]
    normalized_data_json: dict[str, Any]
    status: ImportRowStatus
    validation_errors_json: Optional[list[str]] = None
    match_customer_id: Optional[UUID] = None
    match_customer_name: Optional[str] = None
    match_confidence: Optional[int] = None
    match_reason: Optional[str] = None
    participation_exists: Optional[bool] = None
    suggested_action: Optional[str] = None
    decision: Optional[ImportDecision] = None
    created_customer_id: Optional[UUID] = None
    updated_customer_id: Optional[UUID] = None
    created_participation_id: Optional[UUID] = None
    updated_participation_id: Optional[UUID] = None
    merge_preview: Optional[MergePreviewResponse] = None
    created_at: datetime
    updated_at: datetime


class ImportRowListResponse(StandardListResponse[ImportRowResponse]):
    counts: Optional["ImportRowFilterCountsResponse"] = None


class ImportRowFilterCountsResponse(BaseModel):
    pending: int = 0
    all: int = 0
    applied: int = 0
    new: int = 0
    will_update: int = 0
    duplicate: int = 0
    invalid: int = 0
    skip: int = 0


class SetImportRowDecisionRequest(BaseModel):
    decision: ImportDecision
    match_customer_id: Optional[UUID] = None


class BulkRowDecisionRequest(BaseModel):
    action: str | None = Field(
        default=None,
        description="Legacy: create_all_new | link_all_existing | update_all_duplicates | skip_invalid",
    )
    row_ids: list[UUID] | None = Field(default=None, min_length=1)
    decision: ImportDecision | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "BulkRowDecisionRequest":
        legacy = self.action is not None
        selection = self.row_ids is not None and self.decision is not None
        if legacy == selection:
            raise ValueError("Provide either action or row_ids with decision")
        if selection:
            if not self.row_ids:
                raise ValueError("row_ids must not be empty")
            allowed = {
                ImportDecision.CREATE_NEW,
                ImportDecision.UPDATE_EXISTING,
                ImportDecision.SKIP,
            }
            if self.decision not in allowed:
                raise ValueError("Bulk decision supports create_new, update_existing, skip only")
        return self


class ColumnMappingSpec(BaseModel):
    type: str = "column_index"
    value: int


class MappingColumnStatsResponse(BaseModel):
    total: int
    empty: int
    filled: int
    first_value: str | None = None


class MappingColumnPreviewResponse(BaseModel):
    key: str
    index: int
    letter: str
    header: str | None = None
    samples: list[Any]
    stats: MappingColumnStatsResponse


class ExcelGridPreviewResponse(BaseModel):
    columns: list[dict[str, Any]]
    rows: list[list[Any]]
    total_data_rows: int
    preview_row_count: int


class MappingPreviewResponse(BaseModel):
    batch_id: UUID
    header_mode: ExcelHeaderMode
    header_row_index: int | None = None
    columns: list[MappingColumnPreviewResponse]
    grid: ExcelGridPreviewResponse | None = None


class ConfigureImportHeaderRequest(BaseModel):
    has_header_row: bool = True
    header_mode: ExcelHeaderMode | None = None
    header_row_index: int | None = Field(default=None, ge=0)


class ConfigureImportHeaderResponse(BaseModel):
    batch_id: UUID
    status: ImportBatchStatus
    header_mode: ExcelHeaderMode
    header_row_index: int | None = None
    has_header_row: bool


class SetColumnMappingRequest(BaseModel):
    has_header_row: bool = True
    header_mode: ExcelHeaderMode | None = None
    header_row_index: int | None = Field(default=None, ge=0)
    mappings: dict[str, ColumnMappingSpec]


class UploadRawImportResponse(BaseModel):
    batch_id: UUID
    fair_id: UUID
    source_type: ImportSourceType
    file_name: str
    status: ImportBatchStatus
    detected_headers: list[Any]
    raw_columns: list[dict[str, Any]]
    mapping_columns: list[MappingColumnPreviewResponse] = []
    sample_rows: list[list[Any]]
    total_rows: int
    suggested_mapping: dict[str, Any]
    available_sheets: list[str] = []
    selected_sheet_name: str | None = None


class SetColumnMappingResponse(BaseModel):
    batch_id: UUID
    status: ImportBatchStatus
    column_mapping: dict[str, Any]


class AnalyzeImportResponse(BaseModel):
    batch: ImportBatchResponse
    total_rows: int


class BulkRowDecisionErrorItemResponse(BaseModel):
    row_id: UUID
    row_number: int
    message: str


class BulkRowDecisionResponse(BaseModel):
    updated_count: int
    skipped_count: int = 0
    errors: list[BulkRowDecisionErrorItemResponse] = Field(default_factory=list)


class BulkDecisionPreviewRequest(BaseModel):
    action_type: str = Field(
        ...,
        description="create_all_new | link_all_existing | update_all_duplicates | skip_invalid",
    )


class BulkDecisionPreviewResponse(BaseModel):
    batch_id: UUID
    action_type: str
    affected_rows: int
    already_decided_rows: int
    summary: str
    to_process_rows: int = 0
    skipped_already_linked_rows: int = 0
    unprocessable_rows: int = 0


class BulkDecisionApplyRequest(BaseModel):
    action_type: str = Field(
        ...,
        description="create_all_new | link_all_existing | update_all_duplicates | skip_invalid",
    )


class ApplyImportDecisionErrorItem(BaseModel):
    row_id: UUID
    row_number: int
    message: str


class ApplyImportDecisionsRequest(BaseModel):
    row_ids: list[UUID] | None = Field(
        default=None,
        description="Apply only these rows. When omitted, filter scope is used.",
    )
    filter: str | None = Field(
        default=None,
        description="Decision list filter when row_ids omitted (default: pending).",
    )
    search: str | None = Field(default=None, description="Optional company name search scope.")


class ApplyImportDecisionsResponse(BaseModel):
    processed_count: int
    not_processed_count: int
    failed_count: int
    errors: list[ApplyImportDecisionErrorItem]


class DeleteImportBatchResponse(BaseModel):
    batch_id: UUID
    deleted: bool = True


class ApplyImportResponse(BaseModel):
    batch: ImportBatchResponse
    created_rows: int
    updated_rows: int
    skipped_rows: int
    invalid_rows: int
    created_participations: int = 0
    updated_participations: int = 0
    created_contacts: int = 0


class ErrorResponse(BaseModel):
    detail: str


class CreateImportBatchFromCanonicalResponse(BaseModel):
    batch: ImportBatchResponse
    row_count: int

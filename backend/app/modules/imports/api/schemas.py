from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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
    pass


class SetImportRowDecisionRequest(BaseModel):
    decision: ImportDecision
    match_customer_id: Optional[UUID] = None


class BulkRowDecisionRequest(BaseModel):
    action: str = Field(
        ...,
        description="create_all_new | link_all_existing | update_all_duplicates | skip_invalid",
    )


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


class MappingPreviewResponse(BaseModel):
    batch_id: UUID
    header_mode: ExcelHeaderMode
    header_row_index: int | None = None
    columns: list[MappingColumnPreviewResponse]


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


class BulkRowDecisionResponse(BaseModel):
    updated_count: int


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

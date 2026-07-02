from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.modules.imports.domain.value_objects import (
    ExcelHeaderMode,
    ImportBatchStatus,
    ImportDecision,
    ImportRowStatus,
    ImportSourceType,
)


@dataclass(frozen=True)
class UploadImportCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    file_name: str
    file_content: bytes


@dataclass(frozen=True)
class UploadRawImportCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    fair_id: UUID
    file_name: str
    file_content: bytes


@dataclass(frozen=True)
class SetColumnMappingCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID
    has_header_row: bool
    mappings: dict[str, dict[str, Any]]
    header_mode: ExcelHeaderMode | None = None
    header_row_index: int | None = None


@dataclass(frozen=True)
class ConfigureImportHeaderCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID
    has_header_row: bool
    header_mode: ExcelHeaderMode | None = None
    header_row_index: int | None = None


@dataclass(frozen=True)
class SelectImportSheetCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID
    sheet_name: str
    file_content: bytes = b""


@dataclass(frozen=True)
class GetMappingPreviewQuery:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID
    header_mode: ExcelHeaderMode | None = None
    header_row_index: int | None = None


@dataclass(frozen=True)
class ListImportBatchesQuery:
    organization_id: UUID
    page: int = 1
    page_size: int = 25
    sort_by: str = "created_at"
    sort_dir: str = "desc"


@dataclass(frozen=True)
class AnalyzeImportCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID
    from_background_job: bool = False


@dataclass(frozen=True)
class BulkRowDecisionCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID
    action: str | None = None
    row_ids: list[UUID] | None = None
    decision: ImportDecision | None = None


@dataclass(frozen=True)
class PreviewBulkDecisionQuery:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID
    action_type: str


@dataclass(frozen=True)
class PreviewBulkDecisionResult:
    batch_id: UUID
    action_type: str
    affected_rows: int
    already_decided_rows: int
    summary: str
    to_process_rows: int = 0
    skipped_already_linked_rows: int = 0
    unprocessable_rows: int = 0


@dataclass(frozen=True)
class DeleteImportBatchCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID


@dataclass(frozen=True)
class DeleteImportBatchResult:
    batch_id: UUID
    deleted: bool


@dataclass(frozen=True)
class GetImportBatchQuery:
    organization_id: UUID
    batch_id: UUID


@dataclass(frozen=True)
class ListImportRowsQuery:
    organization_id: UUID
    batch_id: UUID
    filter: str | None = None
    search: str | None = None
    page: int = 1
    page_size: int = 25
    sort_by: str | None = None
    sort_dir: str = "asc"


@dataclass(frozen=True)
class SetImportRowDecisionCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID
    row_id: UUID
    decision: ImportDecision
    match_customer_id: UUID | None = None


@dataclass(frozen=True)
class ApplyImportCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID


@dataclass
class ImportBatchResult:
    id: UUID
    organization_id: UUID
    fair_id: Optional[UUID]
    source_type: ImportSourceType
    file_name: str
    status: ImportBatchStatus
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    created_rows: int
    updated_rows: int
    skipped_rows: int
    created_participations: int
    updated_participations: int
    ready_to_create: int
    ready_to_update: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    notes: Optional[str]
    selected_sheet_name: Optional[str] = None
    available_sheets: list[str] | None = None
    header_mode: Optional[str] = None
    has_header_row: Optional[bool] = None
    header_row_index: Optional[int] = None
    column_mapping_json: Optional[dict[str, Any]] = None


@dataclass
class ImportRowResult:
    id: UUID
    batch_id: UUID
    row_number: int
    raw_data_json: dict[str, Any]
    normalized_data_json: dict[str, Any]
    status: ImportRowStatus
    validation_errors_json: Optional[list[str]]
    match_customer_id: Optional[UUID]
    match_customer_name: Optional[str]
    match_confidence: Optional[int]
    match_reason: Optional[str]
    participation_exists: Optional[bool]
    suggested_action: Optional[str]
    decision: Optional[ImportDecision]
    created_customer_id: Optional[UUID]
    updated_customer_id: Optional[UUID]
    created_participation_id: Optional[UUID]
    updated_participation_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    merge_preview: Optional[dict[str, Any]] = None


@dataclass
class ImportRowListResult:
    items: list[ImportRowResult]
    page: int
    page_size: int
    total: int
    total_pages: int
    filter_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class UploadRawImportResult:
    batch_id: UUID
    fair_id: UUID
    source_type: ImportSourceType
    detected_headers: list[Any]
    raw_columns: list[dict[str, Any]]
    mapping_columns: list[dict[str, Any]]
    sample_rows: list[list[Any]]
    total_rows: int
    suggested_mapping: dict[str, Any]
    status: ImportBatchStatus
    file_name: str
    available_sheets: list[str] = field(default_factory=list)
    selected_sheet_name: str | None = None


@dataclass
class SetColumnMappingResult:
    batch_id: UUID
    status: ImportBatchStatus
    column_mapping: dict[str, Any]


@dataclass
class ConfigureImportHeaderResult:
    batch_id: UUID
    status: ImportBatchStatus
    header_mode: ExcelHeaderMode
    header_row_index: int | None
    has_header_row: bool


@dataclass
class AnalyzeImportResult:
    batch: ImportBatchResult
    total_rows: int


@dataclass
class BulkRowDecisionErrorItem:
    row_id: UUID
    row_number: int
    message: str


@dataclass
class BulkRowDecisionResult:
    updated_count: int
    skipped_count: int = 0
    errors: list[BulkRowDecisionErrorItem] = field(default_factory=list)


@dataclass
class ApplyImportResult:
    batch: ImportBatchResult
    created_rows: int
    updated_rows: int
    skipped_rows: int
    invalid_rows: int
    created_participations: int
    updated_participations: int
    created_contacts: int

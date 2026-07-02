from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.imports.api.schemas import (
    AnalyzeImportResponse,
    ApplyImportResponse,
    BulkRowDecisionRequest,
    BulkRowDecisionResponse,
    ColumnMappingSpec,
    ErrorResponse,
    ImportBatchResponse,
    ImportRowListResponse,
    ImportRowResponse,
    SetColumnMappingResponse,
    SetImportRowDecisionRequest,
    UploadRawImportResponse,
)
from app.modules.imports.domain.value_objects import ExcelHeaderMode, ImportDecision


class DataIntegrationSetColumnMappingRequest(BaseModel):
    has_header_row: bool = True
    header_mode: ExcelHeaderMode | None = None
    header_row_index: int | None = Field(default=None, ge=0)
    mappings: dict[str, ColumnMappingSpec]


class SelectImportSheetRequest(BaseModel):
    sheet_name: str


class SelectImportSheetResponse(BaseModel):
    batch_id: UUID
    selected_sheet_name: str
    total_rows: int
    suggested_mapping: dict[str, Any]
    available_sheets: list[str]
    detected_headers: list[Any] = []
    mapping_columns: list[Any] = []
    sample_rows: list[list[Any]] = []


class ImportBatchListResponse(BaseModel):
    items: list[ImportBatchResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class StartImportJobResponse(BaseModel):
    job_id: UUID
    batch_id: UUID
    status: str
    progress_total: int


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    batch_id: UUID
    job_type: str
    status: str
    progress_processed: int
    progress_total: int
    result_json: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


__all__ = [
    "AnalyzeImportResponse",
    "ApplyImportResponse",
    "BulkRowDecisionRequest",
    "BulkRowDecisionResponse",
    "DataIntegrationSetColumnMappingRequest",
    "ErrorResponse",
    "ImportBatchListResponse",
    "ImportBatchResponse",
    "ImportJobResponse",
    "ImportRowListResponse",
    "ImportRowResponse",
    "SelectImportSheetRequest",
    "SelectImportSheetResponse",
    "SetColumnMappingResponse",
    "SetImportRowDecisionRequest",
    "StartImportJobResponse",
    "UploadRawImportResponse",
]

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.imports.domain.value_objects import ImportBatchStatus, ImportDecision, ImportRowStatus, ImportSourceType


class ImportBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
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
    ready_to_create: int = 0
    ready_to_update: int = 0
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None


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
    decision: Optional[ImportDecision] = None
    created_customer_id: Optional[UUID] = None
    updated_customer_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class ImportRowListResponse(BaseModel):
    items: list[ImportRowResponse]
    total: int


class SetImportRowDecisionRequest(BaseModel):
    decision: ImportDecision
    match_customer_id: Optional[UUID] = None


class ApplyImportResponse(BaseModel):
    batch: ImportBatchResponse
    created_rows: int
    updated_rows: int
    skipped_rows: int
    invalid_rows: int


class ErrorResponse(BaseModel):
    detail: str

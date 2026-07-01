from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.modules.imports.domain.value_objects import ImportBatchStatus, ImportDecision, ImportRowStatus, ImportSourceType


@dataclass(frozen=True)
class UploadImportCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    file_name: str
    file_content: bytes


@dataclass(frozen=True)
class GetImportBatchQuery:
    organization_id: UUID
    batch_id: UUID


@dataclass(frozen=True)
class ListImportRowsQuery:
    organization_id: UUID
    batch_id: UUID


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
    ready_to_create: int
    ready_to_update: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    notes: Optional[str]


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
    decision: Optional[ImportDecision]
    created_customer_id: Optional[UUID]
    updated_customer_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime


@dataclass
class ImportRowListResult:
    items: list[ImportRowResult]
    total: int


@dataclass
class ApplyImportResult:
    batch: ImportBatchResult
    created_rows: int
    updated_rows: int
    skipped_rows: int
    invalid_rows: int

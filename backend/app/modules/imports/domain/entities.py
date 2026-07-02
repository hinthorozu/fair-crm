from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from app.modules.imports.domain.value_objects import (
    ExcelHeaderMode,
    ImportBatchStatus,
    ImportDecision,
    ImportJobStatus,
    ImportJobType,
    ImportRowStatus,
    ImportSourceType,
    ImportSuggestedAction,
)


@dataclass
class ImportBatch:
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
    column_mapping_json: Optional[dict[str, Any]]
    raw_preview_json: Optional[dict[str, Any]]
    has_header_row: Optional[bool]
    header_mode: Optional[ExcelHeaderMode]
    header_row_index: Optional[int]
    selected_sheet_name: Optional[str]
    stored_file_content: Optional[bytes]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    notes: Optional[str]

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        fair_id: UUID,
        file_name: str,
        source_type: ImportSourceType = ImportSourceType.EXCEL,
        total_rows: int = 0,
        raw_preview_json: dict[str, Any] | None = None,
        stored_file_content: bytes | None = None,
        now: datetime,
    ) -> "ImportBatch":
        sheet_name = raw_preview_json.get("sheet_name") if raw_preview_json else None
        return cls(
            id=uuid4(),
            organization_id=organization_id,
            fair_id=fair_id,
            source_type=source_type,
            file_name=file_name,
            status=ImportBatchStatus.UPLOADED,
            total_rows=total_rows,
            valid_rows=0,
            invalid_rows=0,
            duplicate_rows=0,
            created_rows=0,
            updated_rows=0,
            skipped_rows=0,
            created_participations=0,
            updated_participations=0,
            column_mapping_json=None,
            raw_preview_json=raw_preview_json,
            has_header_row=None,
            header_mode=None,
            header_row_index=None,
            selected_sheet_name=sheet_name,
            stored_file_content=stored_file_content,
            created_at=now,
            updated_at=now,
            completed_at=None,
            notes=None,
        )

    @classmethod
    def create_legacy(
        cls,
        *,
        organization_id: UUID,
        file_name: str,
        total_rows: int,
        now: datetime,
    ) -> "ImportBatch":
        """Legacy v1 upload without fair context (deprecated)."""
        return cls(
            id=uuid4(),
            organization_id=organization_id,
            fair_id=None,
            source_type=ImportSourceType.EXCEL,
            file_name=file_name,
            status=ImportBatchStatus.UPLOADED,
            total_rows=total_rows,
            valid_rows=0,
            invalid_rows=0,
            duplicate_rows=0,
            created_rows=0,
            updated_rows=0,
            skipped_rows=0,
            created_participations=0,
            updated_participations=0,
            column_mapping_json=None,
            raw_preview_json=None,
            has_header_row=None,
            header_mode=None,
            header_row_index=None,
            selected_sheet_name=None,
            stored_file_content=None,
            created_at=now,
            updated_at=now,
            completed_at=None,
            notes=None,
        )

    def mark_mapped(
        self,
        *,
        mapping: dict[str, Any],
        has_header_row: bool,
        header_mode: ExcelHeaderMode | None = None,
        header_row_index: int | None = None,
        now: datetime,
    ) -> None:
        self.column_mapping_json = mapping
        self.has_header_row = has_header_row
        self.header_mode = header_mode
        self.header_row_index = header_row_index
        self.status = ImportBatchStatus.MAPPED
        self.updated_at = now

    def set_sheet(self, *, sheet_name: str, raw_preview_json: dict[str, Any], now: datetime) -> None:
        self.selected_sheet_name = sheet_name
        self.raw_preview_json = raw_preview_json
        self.total_rows = raw_preview_json.get("total_rows", 0)
        self.updated_at = now

    def mark_analyzed(self, *, now: datetime) -> None:
        self.status = ImportBatchStatus.ANALYZED
        self.updated_at = now

    def mark_previewed(self, *, now: datetime) -> None:
        self.status = ImportBatchStatus.PREVIEWED
        self.updated_at = now

    def mark_applied(self, *, now: datetime) -> None:
        self.status = ImportBatchStatus.APPLIED
        self.completed_at = now
        self.updated_at = now

    def mark_failed(self, *, now: datetime, notes: str | None = None) -> None:
        self.status = ImportBatchStatus.FAILED
        self.completed_at = now
        self.updated_at = now
        if notes:
            self.notes = notes

    def update_counts(
        self,
        *,
        valid_rows: int,
        invalid_rows: int,
        duplicate_rows: int,
        now: datetime,
    ) -> None:
        self.valid_rows = valid_rows
        self.invalid_rows = invalid_rows
        self.duplicate_rows = duplicate_rows
        self.updated_at = now

    def update_apply_counts(
        self,
        *,
        created_rows: int,
        updated_rows: int,
        skipped_rows: int,
        created_participations: int = 0,
        updated_participations: int = 0,
        now: datetime,
    ) -> None:
        self.created_rows = created_rows
        self.updated_rows = updated_rows
        self.skipped_rows = skipped_rows
        self.created_participations = created_participations
        self.updated_participations = updated_participations
        self.updated_at = now


@dataclass
class ImportRow:
    id: UUID
    batch_id: UUID
    organization_id: UUID
    row_number: int
    raw_data_json: dict[str, Any]
    normalized_data_json: dict[str, Any]
    status: ImportRowStatus
    validation_errors_json: Optional[list[str]]
    match_customer_id: Optional[UUID]
    match_confidence: Optional[int]
    match_reason: Optional[str]
    participation_exists: Optional[bool]
    match_participation_id: Optional[UUID]
    suggested_action: Optional[ImportSuggestedAction]
    decision: Optional[ImportDecision]
    created_customer_id: Optional[UUID]
    updated_customer_id: Optional[UUID]
    created_participation_id: Optional[UUID]
    updated_participation_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        batch_id: UUID,
        organization_id: UUID,
        row_number: int,
        raw_data_json: dict[str, Any],
        normalized_data_json: dict[str, Any],
        status: ImportRowStatus,
        validation_errors_json: list[str] | None,
        match_customer_id: UUID | None,
        match_confidence: int | None,
        match_reason: str | None,
        participation_exists: bool | None = None,
        match_participation_id: UUID | None = None,
        suggested_action: ImportSuggestedAction | None = None,
        now: datetime,
    ) -> "ImportRow":
        default_decision = None
        if status == ImportRowStatus.READY_TO_CREATE:
            default_decision = ImportDecision.CREATE_NEW
        elif status in (ImportRowStatus.POSSIBLE_DUPLICATE, ImportRowStatus.READY_TO_UPDATE):
            default_decision = ImportDecision.UPDATE_EXISTING

        return cls(
            id=uuid4(),
            batch_id=batch_id,
            organization_id=organization_id,
            row_number=row_number,
            raw_data_json=raw_data_json,
            normalized_data_json=normalized_data_json,
            status=status,
            validation_errors_json=validation_errors_json,
            match_customer_id=match_customer_id,
            match_confidence=match_confidence,
            match_reason=match_reason,
            participation_exists=participation_exists,
            match_participation_id=match_participation_id,
            suggested_action=suggested_action,
            decision=default_decision,
            created_customer_id=None,
            updated_customer_id=None,
            created_participation_id=None,
            updated_participation_id=None,
            created_at=now,
            updated_at=now,
        )

    def set_decision(self, decision: ImportDecision, *, now: datetime) -> None:
        self.decision = decision
        self.updated_at = now

    def mark_applied_create(self, customer_id: UUID, *, now: datetime) -> None:
        self.status = ImportRowStatus.APPLIED
        self.created_customer_id = customer_id
        self.updated_at = now

    def mark_applied_update(self, customer_id: UUID, *, now: datetime) -> None:
        self.status = ImportRowStatus.APPLIED
        self.updated_customer_id = customer_id
        self.updated_at = now

    def mark_participation_created(self, participation_id: UUID, *, now: datetime) -> None:
        self.created_participation_id = participation_id
        self.updated_at = now

    def mark_participation_updated(self, participation_id: UUID, *, now: datetime) -> None:
        self.updated_participation_id = participation_id
        self.updated_at = now

    def mark_skipped(self, *, now: datetime) -> None:
        self.status = ImportRowStatus.SKIPPED
        self.updated_at = now

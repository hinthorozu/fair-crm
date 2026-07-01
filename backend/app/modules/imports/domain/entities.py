from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from app.modules.imports.domain.value_objects import (
    ImportBatchStatus,
    ImportDecision,
    ImportRowStatus,
)


@dataclass
class ImportBatch:
    id: UUID
    organization_id: UUID
    file_name: str
    status: ImportBatchStatus
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    created_rows: int
    updated_rows: int
    skipped_rows: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    notes: Optional[str]

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        file_name: str,
        total_rows: int,
        now: datetime,
    ) -> "ImportBatch":
        return cls(
            id=uuid4(),
            organization_id=organization_id,
            file_name=file_name,
            status=ImportBatchStatus.UPLOADED,
            total_rows=total_rows,
            valid_rows=0,
            invalid_rows=0,
            duplicate_rows=0,
            created_rows=0,
            updated_rows=0,
            skipped_rows=0,
            created_at=now,
            updated_at=now,
            completed_at=None,
            notes=None,
        )

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
        now: datetime,
    ) -> None:
        self.created_rows = created_rows
        self.updated_rows = updated_rows
        self.skipped_rows = skipped_rows
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
    decision: Optional[ImportDecision]
    created_customer_id: Optional[UUID]
    updated_customer_id: Optional[UUID]
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
        now: datetime,
    ) -> "ImportRow":
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
            decision=None,
            created_customer_id=None,
            updated_customer_id=None,
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

    def mark_skipped(self, *, now: datetime) -> None:
        self.status = ImportRowStatus.SKIPPED
        self.updated_at = now

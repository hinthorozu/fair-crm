from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from app.modules.operations.domain.exceptions import (
    InvalidOperationStatusError,
    InvalidOperationStatusTransitionError,
    InvalidOperationTitleError,
    InvalidRunItemStatusError,
    InvalidRunStatusError,
    InvalidRunStatusTransitionError,
)
from app.modules.operations.domain.source_normalization import normalize_source_kind
from app.modules.operations.domain.value_objects import (
    OperationPriority,
    OperationStatus,
    OperationType,
    RunItemStatus,
    RunStatus,
    SourceKind,
)

_OPERATION_TRANSITIONS: dict[str, frozenset[str]] = {
    OperationStatus.DRAFT: frozenset(
        {OperationStatus.READY, OperationStatus.ACTIVE, OperationStatus.CANCELLED}
    ),
    OperationStatus.READY: frozenset(
        {
            OperationStatus.ACTIVE,
            OperationStatus.CANCELLED,
            OperationStatus.DRAFT,
        }
    ),
    OperationStatus.ACTIVE: frozenset(
        {
            OperationStatus.COMPLETED,
            OperationStatus.CANCELLED,
            OperationStatus.READY,
        }
    ),
    OperationStatus.COMPLETED: frozenset({OperationStatus.ARCHIVED}),
    OperationStatus.CANCELLED: frozenset({OperationStatus.ARCHIVED, OperationStatus.READY}),
    OperationStatus.ARCHIVED: frozenset(),
}

_RUN_TRANSITIONS: dict[str, frozenset[str]] = {
    RunStatus.QUEUED: frozenset(
        {RunStatus.RUNNING, RunStatus.CANCELLED, RunStatus.FAILED}
    ),
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.PAUSED,
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        }
    ),
    RunStatus.PAUSED: frozenset(
        {RunStatus.RUNNING, RunStatus.CANCELLED, RunStatus.FAILED}
    ),
    RunStatus.COMPLETED: frozenset(),
    RunStatus.FAILED: frozenset({RunStatus.QUEUED}),
    RunStatus.CANCELLED: frozenset(),
}


def _validate_operation_status(value: str) -> str:
    try:
        return OperationStatus(value)
    except ValueError as exc:
        raise InvalidOperationStatusError(f"Invalid operation status: {value}") from exc


def _validate_run_status(value: str) -> str:
    try:
        return RunStatus(value)
    except ValueError as exc:
        raise InvalidRunStatusError(f"Invalid run status: {value}") from exc


def _validate_run_item_status(value: str) -> str:
    try:
        return RunItemStatus(value)
    except ValueError as exc:
        raise InvalidRunItemStatusError(f"Invalid run item status: {value}") from exc


def _validate_source_kind(value: str) -> str:
    return normalize_source_kind(value)


@dataclass
class Operation:
    id: UUID
    organization_id: UUID
    operation_type: str
    title: str
    status: str
    source_kind: str
    source_config: dict[str, Any]
    type_config: dict[str, Any]
    run_settings: dict[str, Any]
    created_by: UUID
    updated_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None
    priority: str = OperationPriority.NORMAL
    latest_run_id: Optional[UUID] = None
    related_todo_id: Optional[UUID] = None

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        operation_type: str,
        title: str,
        created_by: UUID,
        now: datetime,
        source_kind: str = SourceKind.NONE,
        source_config: Optional[dict[str, Any]] = None,
        type_config: Optional[dict[str, Any]] = None,
        run_settings: Optional[dict[str, Any]] = None,
        description: Optional[str] = None,
        priority: str = OperationPriority.NORMAL,
        status: str = OperationStatus.DRAFT,
    ) -> "Operation":
        trimmed_title = title.strip()
        if not trimmed_title:
            raise InvalidOperationTitleError("title must not be empty")

        try:
            OperationType(operation_type)
        except ValueError as exc:
            from app.modules.operations.domain.exceptions import InvalidOperationTypeError

            raise InvalidOperationTypeError(f"Unknown operation type: {operation_type}") from exc
        OperationPriority(priority)

        return cls(
            id=uuid4(),
            organization_id=organization_id,
            operation_type=operation_type,
            title=trimmed_title,
            description=description.strip() if description else None,
            status=_validate_operation_status(status),
            source_kind=_validate_source_kind(source_kind),
            source_config=dict(source_config or {}),
            type_config=dict(type_config or {}),
            run_settings=dict(run_settings or {}),
            priority=priority,
            created_by=created_by,
            updated_by=None,
            latest_run_id=None,
            related_todo_id=None,
            created_at=now,
            updated_at=now,
        )

    def transition_status(self, new_status: str, *, now: datetime, updated_by: UUID) -> None:
        target = _validate_operation_status(new_status)
        allowed = _OPERATION_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise InvalidOperationStatusTransitionError(
                f"Cannot transition operation from {self.status} to {target}"
            )
        self.status = target
        self.updated_by = updated_by
        self.updated_at = now

    def mark_latest_run(self, run_id: UUID, *, now: datetime, updated_by: UUID) -> None:
        self.latest_run_id = run_id
        self.updated_by = updated_by
        self.updated_at = now

    def link_related_todo(self, todo_id: UUID, *, now: datetime, updated_by: UUID) -> None:
        self.related_todo_id = todo_id
        self.updated_by = updated_by
        self.updated_at = now


@dataclass
class OperationRun:
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
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: dict[str, Any] = field(default_factory=dict)
    core_job_id: Optional[UUID] = None
    triggered_by: Optional[UUID] = None

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        operation_id: UUID,
        now: datetime,
        triggered_by: Optional[UUID] = None,
        total_items: int = 0,
        attempt: int = 1,
        status: str = RunStatus.QUEUED,
        core_job_id: Optional[UUID] = None,
    ) -> "OperationRun":
        return cls(
            id=uuid4(),
            organization_id=organization_id,
            operation_id=operation_id,
            status=_validate_run_status(status),
            progress=0.0,
            total_items=max(0, total_items),
            processed_items=0,
            succeeded_items=0,
            failed_items=0,
            attempt=max(1, attempt),
            started_at=None,
            finished_at=None,
            error_code=None,
            error_message=None,
            error_details={},
            core_job_id=core_job_id,
            triggered_by=triggered_by,
            created_at=now,
            updated_at=now,
        )

    def transition_status(self, new_status: str, *, now: datetime) -> None:
        target = _validate_run_status(new_status)
        allowed = _RUN_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise InvalidRunStatusTransitionError(
                f"Cannot transition run from {self.status} to {target}"
            )
        previous = self.status
        self.status = target
        self.updated_at = now
        if target == RunStatus.RUNNING and self.started_at is None:
            self.started_at = now
        if target in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            self.finished_at = now
            if self.total_items > 0:
                self.progress = min(
                    1.0,
                    self.processed_items / self.total_items,
                )
            elif target == RunStatus.COMPLETED:
                self.progress = 1.0
        if previous == RunStatus.FAILED and target == RunStatus.QUEUED:
            self.finished_at = None
            self.error_code = None
            self.error_message = None
            self.error_details = {}

    def mark_failed(
        self,
        *,
        now: datetime,
        error_code: str,
        error_message: str,
        error_details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.transition_status(RunStatus.FAILED, now=now)
        self.error_code = error_code
        self.error_message = error_message
        self.error_details = dict(error_details or {})

    def update_progress(
        self,
        *,
        now: datetime,
        processed_items: Optional[int] = None,
        succeeded_items: Optional[int] = None,
        failed_items: Optional[int] = None,
        total_items: Optional[int] = None,
    ) -> None:
        if total_items is not None:
            self.total_items = max(0, total_items)
        if processed_items is not None:
            self.processed_items = max(0, processed_items)
        if succeeded_items is not None:
            self.succeeded_items = max(0, succeeded_items)
        if failed_items is not None:
            self.failed_items = max(0, failed_items)
        if self.total_items > 0:
            self.progress = min(1.0, self.processed_items / self.total_items)
        self.updated_at = now


@dataclass
class OperationRunItem:
    id: UUID
    organization_id: UUID
    run_id: UUID
    operation_id: UUID
    status: str
    attempt: int
    created_at: datetime
    updated_at: datetime
    item_key: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[UUID] = None
    payload: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        run_id: UUID,
        operation_id: UUID,
        now: datetime,
        item_key: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[UUID] = None,
        payload: Optional[dict[str, Any]] = None,
        status: str = RunItemStatus.PENDING,
        attempt: int = 1,
    ) -> "OperationRunItem":
        return cls(
            id=uuid4(),
            organization_id=organization_id,
            run_id=run_id,
            operation_id=operation_id,
            item_key=item_key,
            target_type=target_type,
            target_id=target_id,
            status=_validate_run_item_status(status),
            attempt=max(1, attempt),
            payload=dict(payload or {}),
            result={},
            error_code=None,
            error_message=None,
            started_at=None,
            finished_at=None,
            created_at=now,
            updated_at=now,
        )

    def mark_processing(self, *, now: datetime) -> None:
        self.status = RunItemStatus.PROCESSING
        if self.started_at is None:
            self.started_at = now
        self.updated_at = now

    def mark_succeeded(
        self,
        *,
        now: datetime,
        result: Optional[dict[str, Any]] = None,
    ) -> None:
        self.status = RunItemStatus.SUCCEEDED
        self.result = dict(result or {})
        self.error_code = None
        self.error_message = None
        self.finished_at = now
        self.updated_at = now

    def mark_failed(
        self,
        *,
        now: datetime,
        error_code: str,
        error_message: str,
        result: Optional[dict[str, Any]] = None,
    ) -> None:
        self.status = RunItemStatus.FAILED
        self.error_code = error_code
        self.error_message = error_message
        self.result = dict(result or {})
        self.finished_at = now
        self.updated_at = now

    def mark_skipped(self, *, now: datetime, reason: Optional[str] = None) -> None:
        self.status = RunItemStatus.SKIPPED
        if reason:
            self.result = {**self.result, "skip_reason": reason}
        self.finished_at = now
        self.updated_at = now

    def mark_cancelled(self, *, now: datetime) -> None:
        self.status = RunItemStatus.CANCELLED
        self.finished_at = now
        self.updated_at = now

    def prepare_retry(self, *, now: datetime) -> None:
        self.attempt += 1
        self.status = RunItemStatus.PENDING
        self.started_at = None
        self.finished_at = None
        self.error_code = None
        self.error_message = None
        self.updated_at = now

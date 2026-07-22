from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.modules.operations.domain.entities import Operation, OperationRun, OperationRunItem
from app.modules.operations.domain.value_objects import OperationPriority, OperationStatus, SourceKind


@dataclass
class CreateOperationCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    operation_type: str
    title: str
    source_kind: str = SourceKind.NONE
    source_ids: list[UUID] = field(default_factory=list)
    source_config: dict[str, Any] = field(default_factory=dict)
    type_config: dict[str, Any] = field(default_factory=dict)
    run_settings: dict[str, Any] = field(default_factory=dict)
    description: Optional[str] = None
    priority: str = OperationPriority.NORMAL
    status: str = OperationStatus.DRAFT
    start_immediately: bool = False


@dataclass
class GetOperationQuery:
    organization_id: UUID
    operation_id: UUID


@dataclass
class ListOperationsQuery:
    organization_id: UUID
    operation_type: Optional[str] = None
    status: Optional[str] = None
    search: Optional[str] = None
    page: int = 1
    page_size: int = 25
    sort_by: str = "created_at"
    sort_dir: str = "desc"


@dataclass
class StartOperationCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    operation_id: UUID


@dataclass
class CancelOperationCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    operation_id: UUID
    run_id: Optional[UUID] = None


@dataclass
class RetryOperationCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    operation_id: UUID
    run_id: Optional[UUID] = None


@dataclass
class ListOperationRunsQuery:
    organization_id: UUID
    operation_id: UUID
    page: int = 1
    page_size: int = 25
    sort_by: str = "created_at"
    sort_dir: str = "desc"


@dataclass
class OperationResult:
    id: UUID
    organization_id: UUID
    operation_type: str
    title: str
    description: Optional[str]
    status: str
    source_kind: str
    source_ids: list[UUID]
    source_config: dict[str, Any]
    type_config: dict[str, Any]
    run_settings: dict[str, Any]
    priority: str
    latest_run_id: Optional[UUID]
    created_by: UUID
    updated_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    related_todo_id: Optional[UUID] = None
    related_resource: Optional[dict[str, Any]] = None
    capabilities: dict[str, bool] = field(default_factory=dict)
    latest_run: Optional["OperationRunResult"] = None


@dataclass
class OperationRunResult:
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


@dataclass
class OperationRunItemResult:
    id: UUID
    organization_id: UUID
    run_id: UUID
    operation_id: UUID
    item_key: Optional[str]
    target_type: Optional[str]
    target_id: Optional[UUID]
    status: str
    attempt: int
    payload: dict[str, Any]
    result: dict[str, Any]
    error_code: Optional[str]
    error_message: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


@dataclass
class OperationDetailResult:
    operation: OperationResult
    runs: list[OperationRunResult]


@dataclass
class WizardMetadataResult:
    types: list[dict[str, Any]]
    source_kinds: list[str]
    capabilities_keys: list[str]

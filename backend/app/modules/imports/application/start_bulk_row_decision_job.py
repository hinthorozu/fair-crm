from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.data_integration.application.import_job_runner import BulkDecisionJobCommand
from app.modules.data_integration.domain.entities import ImportJob
from app.modules.data_integration.domain.ports import ImportJobRepository
from app.modules.imports.domain.exceptions import (
    ImportBatchAlreadyAppliedError,
    ImportBatchNotFoundError,
    ImportBulkActionInProgressError,
)
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository
from app.modules.imports.domain.batch_status import can_open_decisions, is_batch_terminal
from app.modules.imports.domain.services.bulk_decision_actions import BULK_DECISION_ACTIONS

PERMISSION_UPDATE = "fair_crm.imports.update"


@dataclass
class StartBulkRowDecisionJobCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID
    action_type: str


@dataclass
class StartBulkRowDecisionJobResult:
    job_id: UUID
    batch_id: UUID
    status: str
    progress_total: int
    bulk_command: BulkDecisionJobCommand


class StartBulkRowDecisionJobUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
        job_repository: ImportJobRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
        self._job_repository = job_repository
        self._authorization = authorization

    def execute(self, command: StartBulkRowDecisionJobCommand) -> StartBulkRowDecisionJobResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        if command.action_type not in BULK_DECISION_ACTIONS:
            raise ValueError(f"Unknown bulk action: {command.action_type}")

        batch = self._batch_repository.get_by_id(command.organization_id, command.batch_id)
        if batch is None:
            raise ImportBatchNotFoundError("Import batch not found")
        if is_batch_terminal(batch.status):
            raise ImportBatchAlreadyAppliedError("Import batch already applied")
        if not can_open_decisions(batch.status):
            raise ImportBatchNotFoundError("Bulk decisions are only available after analyze")

        if self._job_repository.has_active_bulk_or_apply_job_for_batch(
            command.organization_id, command.batch_id
        ):
            raise ImportBulkActionInProgressError()

        rows = self._row_repository.list_by_batch(command.organization_id, command.batch_id)
        now = datetime.now(tz=UTC)
        job = ImportJob.create_bulk_decision_job(
            organization_id=command.organization_id,
            batch_id=command.batch_id,
            action_type=command.action_type,
            progress_total=max(len(rows), 1),
            now=now,
        )
        saved = self._job_repository.add(job)

        bulk_command = BulkDecisionJobCommand(
            organization_id=command.organization_id,
            user_id=command.user_id,
            access_token=command.access_token,
            batch_id=command.batch_id,
            job_id=saved.id,
            action_type=command.action_type,
        )

        return StartBulkRowDecisionJobResult(
            job_id=saved.id,
            batch_id=command.batch_id,
            status=saved.status.value,
            progress_total=saved.progress_total,
            bulk_command=bulk_command,
        )

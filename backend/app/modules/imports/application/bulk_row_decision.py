from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.imports.application.commands import (
    BulkRowDecisionCommand,
    BulkRowDecisionErrorItem,
    BulkRowDecisionResult,
    SetImportRowDecisionCommand,
)
from app.modules.imports.application.set_row_decision import SetImportRowDecisionUseCase
from app.modules.imports.domain.exceptions import (
    ImportBatchAlreadyAppliedError,
    ImportBatchNotFoundError,
    ImportRowNotFoundError,
    InvalidImportDecisionError,
)
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository
from app.modules.imports.domain.batch_status import is_batch_terminal
from app.modules.imports.domain.services.bulk_decision_actions import (
    BULK_DECISION_ACTIONS,
    apply_bulk_decision_to_row,
)

PERMISSION_UPDATE = "fair_crm.imports.update"


class BulkRowDecisionUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
        set_decision_use_case: SetImportRowDecisionUseCase,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
        self._set_decision_use_case = set_decision_use_case
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: BulkRowDecisionCommand) -> BulkRowDecisionResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        batch = self._batch_repository.get_by_id(command.organization_id, command.batch_id)
        if batch is None:
            raise ImportBatchNotFoundError("Import batch not found")
        if is_batch_terminal(batch.status):
            raise ImportBatchAlreadyAppliedError("Import batch already applied")

        if command.row_ids is not None and command.decision is not None:
            return self._assign_selected_rows(command, batch.id)

        if command.action is None or command.action not in BULK_DECISION_ACTIONS:
            raise ValueError(f"Unknown bulk action: {command.action}")

        rows = self._row_repository.list_by_batch(command.organization_id, command.batch_id)
        updated_count = 0
        for row in rows:
            if apply_bulk_decision_to_row(row, command.action):
                updated_count += 1

        if updated_count:
            self._row_repository.update_many(rows)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.import.bulk_decision",
            resource_type="import_batch",
            resource_id=str(batch.id),
            new_values={"action": command.action, "updated_count": updated_count},
            metadata={"user_id": str(command.user_id)},
        )

        return BulkRowDecisionResult(updated_count=updated_count)

    def _assign_selected_rows(self, command: BulkRowDecisionCommand, batch_id: UUID) -> BulkRowDecisionResult:
        assert command.row_ids is not None
        assert command.decision is not None

        result = BulkRowDecisionResult(updated_count=0)
        row_lookup = {
            row.id: row
            for row in self._row_repository.list_by_batch(command.organization_id, command.batch_id)
        }

        for row_id in command.row_ids:
            row = row_lookup.get(row_id)
            if row is None:
                result.skipped_count += 1
                result.errors.append(
                    BulkRowDecisionErrorItem(
                        row_id=row_id,
                        row_number=0,
                        message="Import row not found",
                    )
                )
                continue

            try:
                self._set_decision_use_case.execute(
                    SetImportRowDecisionCommand(
                        organization_id=command.organization_id,
                        user_id=command.user_id,
                        access_token=command.access_token,
                        batch_id=command.batch_id,
                        row_id=row_id,
                        decision=command.decision,
                    )
                )
                result.updated_count += 1
            except InvalidImportDecisionError as exc:
                result.skipped_count += 1
                result.errors.append(
                    BulkRowDecisionErrorItem(
                        row_id=row_id,
                        row_number=row.row_number,
                        message=str(exc),
                    )
                )
            except ImportRowNotFoundError as exc:
                result.skipped_count += 1
                result.errors.append(
                    BulkRowDecisionErrorItem(
                        row_id=row_id,
                        row_number=row.row_number,
                        message=str(exc),
                    )
                )

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.import.bulk_decision_assign",
            resource_type="import_batch",
            resource_id=str(batch_id),
            new_values={
                "decision": command.decision.value,
                "updated_count": result.updated_count,
                "skipped_count": result.skipped_count,
                "row_count": len(command.row_ids),
            },
            metadata={"user_id": str(command.user_id)},
        )

        return result

from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.imports.application.commands import BulkRowDecisionCommand, BulkRowDecisionResult
from app.modules.imports.domain.exceptions import ImportBatchAlreadyAppliedError, ImportBatchNotFoundError
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository
from app.modules.imports.domain.value_objects import ImportBatchStatus, ImportDecision, ImportRowStatus

PERMISSION_UPDATE = "fair_crm.imports.update"


class BulkRowDecisionUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
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
        if batch.status == ImportBatchStatus.APPLIED:
            raise ImportBatchAlreadyAppliedError("Import batch already applied")

        rows = self._row_repository.list_by_batch(command.organization_id, command.batch_id)
        now = datetime.now(tz=UTC)
        updated_count = 0

        for row in rows:
            if row.status == ImportRowStatus.INVALID:
                if command.action == "skip_invalid":
                    row.set_decision(ImportDecision.SKIP, now=now)
                    updated_count += 1
                continue

            if command.action == "create_all_new":
                if row.status == ImportRowStatus.READY_TO_CREATE:
                    row.set_decision(ImportDecision.CREATE_NEW, now=now)
                    updated_count += 1
            elif command.action == "link_all_existing":
                if row.status in (ImportRowStatus.READY_TO_UPDATE, ImportRowStatus.POSSIBLE_DUPLICATE):
                    if row.match_customer_id:
                        row.set_decision(ImportDecision.UPDATE_EXISTING, now=now)
                        updated_count += 1
            elif command.action == "update_all_duplicates":
                if row.status == ImportRowStatus.POSSIBLE_DUPLICATE and row.match_customer_id:
                    row.set_decision(ImportDecision.UPDATE_EXISTING, now=now)
                    updated_count += 1
            elif command.action == "skip_invalid":
                pass

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

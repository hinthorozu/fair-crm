from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.imports.application.commands import PreviewBulkDecisionQuery, PreviewBulkDecisionResult
from app.modules.imports.domain.exceptions import ImportBatchAlreadyAppliedError, ImportBatchNotFoundError
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository
from app.modules.imports.domain.batch_status import can_open_decisions, is_batch_terminal
from app.modules.imports.domain.services.bulk_decision_actions import BULK_DECISION_ACTIONS, preview_bulk_decision
from app.modules.imports.domain.services.bulk_link_existing_to_fair import preview_link_existing_to_fair
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)

PERMISSION_UPDATE = "fair_crm.imports.update"


class PreviewBulkRowDecisionUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
        participation_repository: SqlAlchemyParticipationRepository,
        customer_repository: CustomerRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
        self._participation_repository = participation_repository
        self._customer_repository = customer_repository
        self._authorization = authorization

    def execute(self, query: PreviewBulkDecisionQuery) -> PreviewBulkDecisionResult:
        if not self._authorization.check_permission(
            organization_id=query.organization_id,
            user_id=query.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=query.access_token,
        ):
            raise ForbiddenError("Permission denied")

        if query.action_type not in BULK_DECISION_ACTIONS:
            raise ValueError(f"Unknown bulk action: {query.action_type}")

        batch = self._batch_repository.get_by_id(query.organization_id, query.batch_id)
        if batch is None:
            raise ImportBatchNotFoundError("Import batch not found")
        if is_batch_terminal(batch.status):
            raise ImportBatchAlreadyAppliedError("Import batch already applied")
        if not can_open_decisions(batch.status):
            raise ImportBatchNotFoundError("Bulk decisions are only available after analyze")

        rows = self._row_repository.list_by_batch(query.organization_id, query.batch_id)

        if query.action_type == "link_all_existing":
            preview = preview_link_existing_to_fair(
                rows,
                fair_id=batch.fair_id,
                participation_lookup=self._participation_repository,
                customer_lookup=self._customer_repository,
                organization_id=query.organization_id,
            )
            return PreviewBulkDecisionResult(
                batch_id=query.batch_id,
                action_type=preview.action_type,
                affected_rows=preview.affected_rows,
                already_decided_rows=preview.already_decided_rows,
                summary=preview.summary,
                to_process_rows=preview.to_process_rows,
                skipped_already_linked_rows=preview.skipped_already_linked_rows,
                unprocessable_rows=preview.unprocessable_rows,
            )

        preview = preview_bulk_decision(rows, query.action_type)
        return PreviewBulkDecisionResult(
            batch_id=query.batch_id,
            action_type=preview.action_type,
            affected_rows=preview.affected_rows,
            already_decided_rows=preview.already_decided_rows,
            summary=preview.summary,
        )

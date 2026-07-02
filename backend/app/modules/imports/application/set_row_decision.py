from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.contacts.infrastructure.repositories.contact_repository import SqlAlchemyContactRepository
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.imports.application.commands import ImportRowResult, SetImportRowDecisionCommand
from app.modules.imports.application.mappers import row_to_result
from app.modules.imports.application.merge_preview_builder import MergePreviewBuilder
from app.modules.imports.domain.exceptions import (
    ImportBatchAlreadyAppliedError,
    ImportBatchNotFoundError,
    ImportRowNotFoundError,
    InvalidImportDecisionError,
)
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository
from app.modules.imports.domain.batch_status import is_batch_terminal
from app.modules.imports.domain.value_objects import ImportDecision, ImportRowStatus
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)

PERMISSION_UPDATE = "fair_crm.imports.update"


class SetImportRowDecisionUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
        customer_repository: CustomerRepository,
        participation_repository: SqlAlchemyParticipationRepository,
        contact_repository: SqlAlchemyContactRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
        self._customer_repository = customer_repository
        self._preview_builder = MergePreviewBuilder(
            customer_repository,
            participation_repository,
            contact_repository,
        )
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: SetImportRowDecisionCommand) -> ImportRowResult:
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

        row = self._row_repository.get_by_id(
            command.organization_id, command.batch_id, command.row_id
        )
        if row is None:
            raise ImportRowNotFoundError("Import row not found")

        self._validate_decision(row, command)

        now = datetime.now(tz=UTC)
        row.set_decision(command.decision, now=now)

        if command.decision == ImportDecision.UPDATE_EXISTING:
            target_id = command.match_customer_id or row.match_customer_id
            if target_id is None:
                raise InvalidImportDecisionError("match_customer_id is required for update_existing")
            customer = self._customer_repository.get_by_id(command.organization_id, target_id)
            if customer is None:
                raise InvalidImportDecisionError("Matched customer not found")
            row.match_customer_id = target_id
            row.status = ImportRowStatus.READY_TO_UPDATE
        elif command.decision == ImportDecision.CREATE_NEW:
            row.match_customer_id = None
            row.status = ImportRowStatus.READY_TO_CREATE
        elif command.decision == ImportDecision.PARTICIPATION_ONLY:
            target_id = command.match_customer_id or row.match_customer_id
            if target_id is None:
                raise InvalidImportDecisionError("match_customer_id is required for participation_only")
            row.match_customer_id = target_id
            row.status = ImportRowStatus.READY_TO_UPDATE
        elif command.decision == ImportDecision.MANUAL_REVIEW:
            row.status = ImportRowStatus.POSSIBLE_DUPLICATE

        saved = self._row_repository.update(row)
        merge_preview = self._preview_builder.build_for_row(command.organization_id, batch, saved)

        match_name = None
        if saved.match_customer_id:
            customer = self._customer_repository.get_by_id(
                command.organization_id, saved.match_customer_id
            )
            if customer:
                match_name = customer.display_name

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.import.row_decision_set",
            resource_type="import_row",
            resource_id=str(saved.id),
            new_values={"decision": saved.decision.value if saved.decision else None},
            metadata={"user_id": str(command.user_id), "batch_id": str(command.batch_id)},
        )

        return row_to_result(saved, match_customer_name=match_name, merge_preview=merge_preview)

    def _validate_decision(self, row, command: SetImportRowDecisionCommand) -> None:
        if row.status == ImportRowStatus.INVALID:
            if command.decision != ImportDecision.SKIP:
                raise InvalidImportDecisionError("Invalid rows can only be skipped")
            return

        if command.decision == ImportDecision.CREATE_NEW:
            if row.status == ImportRowStatus.INVALID:
                raise InvalidImportDecisionError("Cannot create from invalid row")
            return

        if command.decision == ImportDecision.UPDATE_EXISTING:
            target_id = command.match_customer_id or row.match_customer_id
            if target_id is None:
                raise InvalidImportDecisionError("match_customer_id is required for update_existing")
            return

        if command.decision == ImportDecision.SKIP:
            return

        if command.decision == ImportDecision.MANUAL_REVIEW:
            return

        if command.decision == ImportDecision.PARTICIPATION_ONLY:
            target_id = command.match_customer_id or row.match_customer_id
            if target_id is None:
                raise InvalidImportDecisionError("match_customer_id is required for participation_only")
            return

        raise InvalidImportDecisionError("Unsupported decision")

from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.imports.application.column_mapper import apply_column_mapping
from app.modules.imports.application.commands import AnalyzeImportCommand, AnalyzeImportResult
from app.modules.imports.application.import_row_builder import build_import_rows
from app.modules.imports.application.mappers import batch_to_result
from app.modules.imports.domain.exceptions import (
    ImportBatchAlreadyAppliedError,
    ImportBatchNotFoundError,
    InvalidColumnMappingError,
)
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository
from app.modules.imports.domain.value_objects import ImportBatchStatus, ImportRowStatus
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)

PERMISSION_UPDATE = "fair_crm.imports.update"


class AnalyzeImportUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
        customer_repository: CustomerRepository,
        participation_repository: SqlAlchemyParticipationRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
        self._customer_repository = customer_repository
        self._participation_repository = participation_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: AnalyzeImportCommand) -> AnalyzeImportResult:
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
        if batch.raw_preview_json is None:
            raise InvalidColumnMappingError("No raw preview data on batch")
        if batch.column_mapping_json is None:
            raise InvalidColumnMappingError("company_name mapping is required")

        now = datetime.now(tz=UTC)
        mapped_rows = apply_column_mapping(batch.raw_preview_json, batch.column_mapping_json)
        customers = self._customer_repository.list_all_active(command.organization_id)
        fair_id = batch.fair_id

        def participation_lookup(customer_id: UUID) -> tuple[bool, UUID | None]:
            if fair_id is None:
                return False, None
            participation = self._participation_repository.get_active_by_customer_and_fair(
                command.organization_id, customer_id, fair_id
            )
            if participation:
                return True, participation.id
            return False, None

        import_rows = build_import_rows(
            batch=batch,
            raw_rows=mapped_rows,
            customers=customers,
            fair_id=fair_id,
            participation_exists=participation_lookup if fair_id else None,
            now=now,
        )

        self._row_repository.delete_by_batch(command.organization_id, command.batch_id)
        saved_rows = self._row_repository.add_many(import_rows)

        valid_count = sum(
            1
            for row in saved_rows
            if row.status
            in (
                ImportRowStatus.READY_TO_CREATE,
                ImportRowStatus.READY_TO_UPDATE,
                ImportRowStatus.POSSIBLE_DUPLICATE,
            )
        )
        invalid_count = sum(1 for row in saved_rows if row.status == ImportRowStatus.INVALID)
        duplicate_count = sum(
            1 for row in saved_rows if row.status == ImportRowStatus.POSSIBLE_DUPLICATE
        )

        batch.total_rows = len(saved_rows)
        batch.mark_analyzed(now=now)
        batch.update_counts(
            valid_rows=valid_count,
            invalid_rows=invalid_count,
            duplicate_rows=duplicate_count,
            now=now,
        )
        updated_batch = self._batch_repository.update(batch)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.import.analyzed",
            resource_type="import_batch",
            resource_id=str(updated_batch.id),
            new_values={"total_rows": updated_batch.total_rows},
            metadata={"user_id": str(command.user_id)},
        )

        batch_result = batch_to_result(updated_batch, saved_rows)
        return AnalyzeImportResult(batch=batch_result, total_rows=len(saved_rows))

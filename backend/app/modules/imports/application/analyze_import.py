from datetime import UTC, datetime
import time
from uuid import UUID

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.core.logging import get_logger
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.imports.application.column_mapper import iter_mapped_rows
from app.modules.imports.application.commands import AnalyzeImportCommand, AnalyzeImportResult
from app.modules.imports.application.import_row_builder import (
    apply_participation_and_status,
    validate_mapped_rows,
)
from app.modules.imports.application.mappers import batch_to_result
from app.modules.imports.domain.entities import ImportRow
from app.modules.imports.domain.batch_status import (
    ACTIVE_ANALYZE_BATCH_STATUSES,
    can_start_analyze,
    is_batch_terminal,
)
from app.modules.imports.domain.exceptions import (
    ImportBatchAlreadyAppliedError,
    ImportBatchAnalyzeNotAllowedError,
    ImportBatchNotFoundError,
    InvalidColumnMappingError,
)
from app.modules.imports.domain.import_limits import ImportLimits
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository
from app.modules.imports.domain.services.duplicate_detector import CustomerMatchIndex
from app.modules.imports.domain.services.merge_preview import assign_default_decision
from app.modules.imports.domain.value_objects import ImportBatchStatus, ImportRowStatus
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)

PERMISSION_UPDATE = "fair_crm.imports.update"
logger = get_logger(__name__)


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
        if is_batch_terminal(batch.status):
            raise ImportBatchAlreadyAppliedError("Import batch already applied")
        if command.from_background_job:
            if batch.status not in ACTIVE_ANALYZE_BATCH_STATUSES:
                raise ImportBatchAnalyzeNotAllowedError("Batch is not queued for analyze")
        elif not can_start_analyze(batch.status):
            raise ImportBatchAnalyzeNotAllowedError(
                "Analyze can only be started after column mapping is completed"
            )
        if batch.raw_preview_json is None:
            raise InvalidColumnMappingError("No raw preview data on batch")
        if batch.column_mapping_json is None:
            raise InvalidColumnMappingError("company_name mapping is required")

        now = datetime.now(tz=UTC)
        started = time.perf_counter()
        limits = ImportLimits.from_settings(get_settings())
        stored_row_count = int((batch.raw_preview_json or {}).get("total_rows") or 0)
        if stored_row_count > limits.max_rows:
            limits.validate_row_count(stored_row_count)

        # Step 6 (customer name match) — first CRM access
        customers = self._customer_repository.list_all_active(command.organization_id)
        customers_elapsed = time.perf_counter()
        customer_index = CustomerMatchIndex.build(customers)
        index_elapsed = time.perf_counter()

        # Step 7 (participation check) — minimal fair + customer lookup
        fair_id = batch.fair_id
        participation_by_customer: dict[UUID, UUID] = {}
        if fair_id is not None:
            participation_by_customer = self._participation_repository.map_active_customer_ids_for_fair(
                command.organization_id,
                fair_id,
            )
        participation_elapsed = time.perf_counter()

        self._row_repository.delete_by_batch(command.organization_id, command.batch_id)

        chunk_size = max(limits.analyze_chunk_size, 1)
        seen_names: dict[str, int] = {}
        saved_rows: list[ImportRow] = []
        mapped_total = 0
        validate_elapsed = customers_elapsed
        match_elapsed = participation_elapsed
        rows_elapsed = participation_elapsed

        mapped_buffer: list[dict] = []
        row_number = 1

        def flush_chunk() -> None:
            nonlocal row_number, mapped_total, validate_elapsed, match_elapsed, rows_elapsed, saved_rows
            if not mapped_buffer:
                return
            mapped_total += len(mapped_buffer)
            validated_chunk = validate_mapped_rows(
                mapped_buffer,
                seen_names=seen_names,
                start_row_number=row_number,
            )
            row_number += len(mapped_buffer)
            validate_elapsed = time.perf_counter()
            matched_chunk = apply_participation_and_status(
                validated_rows=validated_chunk,
                customer_index=customer_index,
                fair_id=fair_id,
                participation_by_customer=participation_by_customer or None,
            )
            match_elapsed = time.perf_counter()
            import_chunk = self._rows_from_matched(batch, matched_chunk, now)
            rows_elapsed = time.perf_counter()
            saved_rows.extend(self._row_repository.add_many(import_chunk))
            mapped_buffer.clear()

        for mapped_row in iter_mapped_rows(batch.raw_preview_json, batch.column_mapping_json):
            mapped_buffer.append(mapped_row)
            if len(mapped_buffer) >= chunk_size:
                flush_chunk()
        flush_chunk()
        map_elapsed = time.perf_counter()

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
        batch.mark_decision_required(now=now)
        batch.update_counts(
            valid_rows=valid_count,
            invalid_rows=invalid_count,
            duplicate_rows=duplicate_count,
            now=now,
        )
        updated_batch = self._batch_repository.update(batch)

        total_elapsed = time.perf_counter() - started
        logger.info(
            "import analyze completed batch_id=%s mapped_rows=%d validated=%d crm_customers=%d "
            "map_ms=%.0f validate_ms=%.0f customers_ms=%.0f index_ms=%.0f "
            "participation_ms=%.0f match_ms=%.0f persist_ms=%.0f total_ms=%.0f chunk_size=%d",
            updated_batch.id,
            mapped_total,
            len(saved_rows),
            len(customers),
            (map_elapsed - started) * 1000,
            (validate_elapsed - map_elapsed) * 1000,
            (customers_elapsed - validate_elapsed) * 1000,
            (index_elapsed - customers_elapsed) * 1000,
            (participation_elapsed - index_elapsed) * 1000,
            (match_elapsed - participation_elapsed) * 1000,
            (rows_elapsed - match_elapsed) * 1000,
            total_elapsed * 1000,
            chunk_size,
        )

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

    @staticmethod
    def _rows_from_matched(batch, matched, now: datetime) -> list[ImportRow]:
        rows: list[ImportRow] = []
        for row, match_fields in matched:
            normalized = dict(row.normalized)
            if match_fields.get("match_explanation"):
                normalized["_match_explanation"] = match_fields["match_explanation"]
            rows.append(
                ImportRow.create(
                    batch_id=batch.id,
                    organization_id=batch.organization_id,
                    row_number=row.row_number,
                    raw_data_json=row.raw,
                    normalized_data_json=normalized,
                    status=match_fields["status"],
                    validation_errors_json=row.errors or None,
                    match_customer_id=match_fields["match_customer_id"],
                    match_confidence=match_fields["match_confidence"],
                    match_reason=match_fields["match_reason"],
                    participation_exists=match_fields["participation_exists"],
                    match_participation_id=match_fields["match_participation_id"],
                    suggested_action=match_fields["suggested_action"],
                    now=now,
                )
            )
            assign_default_decision(rows[-1], now=now)
        return rows

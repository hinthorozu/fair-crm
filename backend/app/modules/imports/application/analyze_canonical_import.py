"""Analyze import batches created from canonical scraper handoff."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.dev_bypass import NoOpAuditAdapter, dev_bypass_enabled
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.imports.application.commands import AnalyzeImportResult
from app.modules.imports.application.import_row_builder import ValidatedRow, apply_participation_and_status
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
)
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository
from app.modules.imports.domain.services.company_name_normalizer import normalize_import_company_name
from app.modules.imports.domain.services.duplicate_detector import CustomerMatchIndex
from app.modules.imports.domain.services.merge_preview import assign_default_decision
from app.modules.imports.domain.value_objects import ImportBatchStatus, ImportRowStatus
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)


class AnalyzeCanonicalImportUseCase:
    """Match CRM customers for rows already loaded from canonical scraper JSON."""

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

    def execute(
        self,
        *,
        organization_id: UUID,
        batch_id: UUID,
        user_id: UUID,
        access_token: str,
        skip_permission_check: bool = False,
        from_background_job: bool = False,
    ) -> AnalyzeImportResult:
        if not skip_permission_check and not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code="fair_crm.imports.update",
            access_token=access_token,
        ):
            from app.core.exceptions import ForbiddenError

            raise ForbiddenError("Permission denied")

        batch = self._batch_repository.get_by_id(organization_id, batch_id)
        if batch is None:
            raise ImportBatchNotFoundError("Import batch not found")
        if is_batch_terminal(batch.status):
            raise ImportBatchAlreadyAppliedError("Import batch already applied")
        if from_background_job:
            if batch.status not in ACTIVE_ANALYZE_BATCH_STATUSES:
                raise ImportBatchAnalyzeNotAllowedError("Batch is not queued for analyze")
        elif batch.status != ImportBatchStatus.RECEIVED and not can_start_analyze(batch.status):
            raise ImportBatchAnalyzeNotAllowedError(
                "Canonical analyze is only allowed for received or decision-pending batches"
            )

        now = datetime.now(tz=UTC)
        is_reanalyze = batch.status not in (
            ImportBatchStatus.RECEIVED,
            ImportBatchStatus.ANALYSIS_QUEUED,
            ImportBatchStatus.ANALYZING,
        )
        existing_rows = self._row_repository.list_by_batch(organization_id, batch_id)
        if not existing_rows:
            batch.mark_decision_required(now=now)
            updated_batch = self._batch_repository.update(batch)
            return AnalyzeImportResult(batch=batch_to_result(updated_batch, []), total_rows=0)

        customers = self._customer_repository.list_all_active(organization_id)
        customer_index = CustomerMatchIndex.build(customers)
        fair_id = batch.fair_id
        participation_by_customer: dict[UUID, UUID] = {}
        if fair_id is not None:
            participation_by_customer = self._participation_repository.map_active_customer_ids_for_fair(
                organization_id,
                fair_id,
            )

        validated_rows = []
        for row in existing_rows:
            normalized = dict(row.normalized_data_json or {})
            if not normalized.get("normalized_company_name") and normalized.get("company_name"):
                normalized["normalized_company_name"] = normalize_import_company_name(
                    str(normalized["company_name"])
                )
            validated_rows.append(
                ValidatedRow(
                    row_number=row.row_number,
                    raw=row.raw_data_json or {},
                    normalized=normalized,
                    errors=list(row.validation_errors_json or []),
                    status=ImportRowStatus.INVALID if row.status == ImportRowStatus.INVALID else ImportRowStatus.VALID,
                )
            )
        matched = apply_participation_and_status(
            validated_rows=validated_rows,
            customer_index=customer_index,
            fair_id=fair_id,
            participation_by_customer=participation_by_customer or None,
        )

        updated_rows: list[ImportRow] = []
        for existing, (validated_row, match_fields) in zip(existing_rows, matched, strict=True):
            normalized = dict(validated_row.normalized)
            if match_fields.get("match_explanation"):
                normalized["_match_explanation"] = match_fields["match_explanation"]
            existing.raw_data_json = validated_row.raw
            existing.normalized_data_json = normalized
            existing.status = match_fields["status"]
            existing.validation_errors_json = validated_row.errors or None
            existing.match_customer_id = match_fields["match_customer_id"]
            existing.match_confidence = match_fields["match_confidence"]
            existing.match_reason = match_fields["match_reason"]
            existing.participation_exists = match_fields["participation_exists"]
            existing.match_participation_id = match_fields["match_participation_id"]
            existing.suggested_action = match_fields["suggested_action"]
            if is_reanalyze:
                existing.decision = None
            assign_default_decision(existing, now=now)
            existing.updated_at = now
            updated_rows.append(existing)

        self._row_repository.update_many(updated_rows)
        saved_rows = updated_rows

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
        duplicate_count = sum(1 for row in saved_rows if row.status == ImportRowStatus.POSSIBLE_DUPLICATE)

        batch.total_rows = len(saved_rows)
        batch.mark_decision_required(now=now)
        batch.update_counts(
            valid_rows=valid_count,
            invalid_rows=invalid_count,
            duplicate_rows=duplicate_count,
            now=now,
        )
        updated_batch = self._batch_repository.update(batch)

        audit = self._audit if not dev_bypass_enabled() else NoOpAuditAdapter()
        audit.record_event(
            organization_id=organization_id,
            access_token=access_token,
            action="fair_crm.import.analyzed",
            resource_type="import_batch",
            resource_id=str(updated_batch.id),
            new_values={"total_rows": updated_batch.total_rows, "source": "canonical_scraper"},
            metadata={"user_id": str(user_id)},
        )

        return AnalyzeImportResult(batch=batch_to_result(updated_batch, saved_rows), total_rows=len(saved_rows))

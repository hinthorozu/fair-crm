from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.imports.application.apply_import import ApplyImportUseCase
from app.modules.imports.application.commands import ApplyImportCommand
from app.modules.imports.domain.exceptions import ImportBatchAlreadyAppliedError, ImportBatchNotFoundError
from app.modules.imports.domain.entities import ImportRow
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository
from app.modules.imports.domain.batch_status import is_batch_terminal
from app.modules.imports.domain.services.merge_preview import row_matches_filter
from app.modules.imports.domain.value_objects import ImportDecision

PERMISSION_APPLY = "fair_crm.imports.apply"


@dataclass
class ApplyImportDecisionsCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID
    row_ids: list[UUID] | None = None
    filter: str | None = None
    search: str | None = None


@dataclass
class ApplyImportDecisionErrorItem:
    row_id: UUID
    row_number: int
    message: str


@dataclass
class ApplyImportDecisionsResult:
    processed_count: int = 0
    not_processed_count: int = 0
    failed_count: int = 0
    errors: list[ApplyImportDecisionErrorItem] = field(default_factory=list)


class ApplyImportDecisionsUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
        apply_use_case: ApplyImportUseCase,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
        self._apply_use_case = apply_use_case
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: ApplyImportDecisionsCommand) -> ApplyImportDecisionsResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_APPLY,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        batch = self._batch_repository.get_by_id(command.organization_id, command.batch_id)
        if batch is None:
            raise ImportBatchNotFoundError("Import batch not found")
        if is_batch_terminal(batch.status):
            raise ImportBatchAlreadyAppliedError("Import batch already applied")

        all_rows = self._row_repository.list_by_batch(command.organization_id, command.batch_id)
        target_rows = self._resolve_target_rows(
            all_rows,
            row_ids=command.row_ids,
            filter_key=command.filter,
            search=command.search,
        )

        result = ApplyImportDecisionsResult()
        apply_cmd = ApplyImportCommand(
            organization_id=command.organization_id,
            user_id=command.user_id,
            access_token=command.access_token,
            batch_id=command.batch_id,
        )
        now = datetime.now(tz=UTC)

        for row in target_rows:
            if row.decision is None:
                result.not_processed_count += 1
                continue

            if row.decision == ImportDecision.MANUAL_REVIEW:
                result.not_processed_count += 1
                continue

            try:
                counters = self._apply_use_case.finalize_applied_row(batch, row, apply_cmd, now)
                if counters.applied:
                    result.processed_count += 1
                else:
                    result.failed_count += 1
                    result.errors.append(
                        ApplyImportDecisionErrorItem(
                            row_id=row.id,
                            row_number=row.row_number,
                            message="Satır uygulanamadı",
                        )
                    )
            except Exception as exc:
                result.failed_count += 1
                result.errors.append(
                    ApplyImportDecisionErrorItem(
                        row_id=row.id,
                        row_number=row.row_number,
                        message=str(exc),
                    )
                )

        remaining_rows = self._row_repository.list_by_batch(command.organization_id, command.batch_id)
        batch = self._apply_use_case.sync_batch_progress(batch, remaining_rows, now=now)
        self._batch_repository.update(batch)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.import.decisions_applied",
            resource_type="import_batch",
            resource_id=str(batch.id),
            new_values={
                "processed_count": result.processed_count,
                "not_processed_count": result.not_processed_count,
                "failed_count": result.failed_count,
            },
            metadata={"user_id": str(command.user_id)},
        )

        return result

    def _resolve_target_rows(
        self,
        rows: list[ImportRow],
        *,
        row_ids: list[UUID] | None,
        filter_key: str | None,
        search: str | None,
    ) -> list[ImportRow]:
        if row_ids is not None:
            id_set = set(row_ids)
            scoped = [row for row in rows if row.id in id_set]
        else:
            fk = filter_key or "pending"
            scoped = [row for row in rows if row_matches_filter(row, fk)]

        term = (search or "").strip().lower()
        if not term:
            return scoped
        return [
            row
            for row in scoped
            if term in str((row.normalized_data_json or {}).get("company_name") or "").lower()
        ]

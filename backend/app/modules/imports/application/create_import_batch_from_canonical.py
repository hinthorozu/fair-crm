"""Create import batch + rows from a canonical import handoff document."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository
from app.modules.imports.application.canonical_batch_mapper import (
    build_import_batch_from_canonical,
    build_import_rows_from_canonical,
)
from app.modules.imports.application.commands import (
    CreateImportBatchFromCanonicalCommand,
    CreateImportBatchFromCanonicalResult,
)
from app.modules.imports.application.mappers import batch_to_result
from app.modules.imports.domain.exceptions import FairRequiredError, InvalidCanonicalImportError
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository
from app.shared.canonical_import.validator import (
    CanonicalImportValidationError,
    validate_canonical_import,
)

PERMISSION_CREATE = "fair_crm.imports.create"


class CreateImportBatchFromCanonicalUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
        fair_repository: FairRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
        self._fair_repository = fair_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: CreateImportBatchFromCanonicalCommand) -> CreateImportBatchFromCanonicalResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        if not command.document:
            raise InvalidCanonicalImportError("Canonical import document is required")

        try:
            validated = validate_canonical_import(command.document)
        except CanonicalImportValidationError as exc:
            raise InvalidCanonicalImportError(str(exc)) from exc

        fair_id = command.fair_id or validated.source.fair_id
        if fair_id is None:
            raise FairRequiredError("fair_id is required (source.fair_id or request body)")

        fair = self._fair_repository.get_by_id(command.organization_id, fair_id)
        if fair is None:
            raise FairNotFoundError("Fair not found")

        now = datetime.now(tz=UTC)
        batch = build_import_batch_from_canonical(
            validated,
            organization_id=command.organization_id,
            fair_id=fair_id,
            now=now,
        )
        saved_batch = self._batch_repository.add(batch)

        rows = build_import_rows_from_canonical(
            validated,
            batch_id=saved_batch.id,
            organization_id=command.organization_id,
            now=now,
        )
        saved_rows = self._row_repository.add_many(rows) if rows else []

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.import.batch_from_canonical",
            resource_type="import_batch",
            resource_id=str(saved_batch.id),
            new_values={
                "source_type": saved_batch.source_type.value,
                "fair_id": str(saved_batch.fair_id),
                "total_rows": saved_batch.total_rows,
                "scraper_run_id": (
                    str(validated.source.run_id) if validated.source.run_id is not None else None
                ),
            },
            metadata={"user_id": str(command.user_id)},
        )

        return CreateImportBatchFromCanonicalResult(
            batch=batch_to_result(saved_batch, saved_rows),
            row_count=len(saved_rows),
        )

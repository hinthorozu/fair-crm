from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.modules.imports.application.apply_import import ApplyImportUseCase
from app.modules.imports.application.commands import ApplyImportCommand, ApplyImportResult


@dataclass
class ImportExecutionResult:
    batch_id: UUID
    created_rows: int
    updated_rows: int
    skipped_rows: int
    invalid_rows: int
    created_participations: int
    updated_participations: int
    created_contacts: int

    @classmethod
    def from_apply(cls, batch_id: UUID, result: ApplyImportResult) -> "ImportExecutionResult":
        return cls(
            batch_id=batch_id,
            created_rows=result.created_rows,
            updated_rows=result.updated_rows,
            skipped_rows=result.skipped_rows,
            invalid_rows=result.invalid_rows,
            created_participations=result.created_participations,
            updated_participations=result.updated_participations,
            created_contacts=result.created_contacts,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": str(self.batch_id),
            "created_rows": self.created_rows,
            "updated_rows": self.updated_rows,
            "skipped_rows": self.skipped_rows,
            "invalid_rows": self.invalid_rows,
            "created_participations": self.created_participations,
            "updated_participations": self.updated_participations,
            "created_contacts": self.created_contacts,
        }


class ImportExecutor:
    """Executes approved import rows into CRM."""

    def __init__(self, apply_use_case: ApplyImportUseCase) -> None:
        self._apply = apply_use_case

    def execute(self, command: ApplyImportCommand) -> ImportExecutionResult:
        result = self._apply.execute(command)
        return ImportExecutionResult.from_apply(command.batch_id, result)

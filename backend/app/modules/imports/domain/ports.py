from typing import Any, Protocol
from uuid import UUID

from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.value_objects import ImportSourceType


class ImportSourceAdapter(Protocol):
    """Extracts canonical raw row dicts from a source-specific payload.

    Future adapters: PdfImportSourceAdapter, ScraperImportSourceAdapter, DatabaseImportSourceAdapter.
    All adapters must output rows keyed by CANONICAL_FIELDS (see header_mapping).
    """

    source_type: ImportSourceType

    def extract_rows(self, payload: bytes, *, file_name: str) -> list[dict[str, Any]]: ...


class ImportBatchRepository(Protocol):
    def add(self, batch: ImportBatch) -> ImportBatch: ...

    def get_by_id(self, organization_id: UUID, batch_id: UUID) -> ImportBatch | None: ...

    def update(self, batch: ImportBatch) -> ImportBatch: ...


class ImportRowRepository(Protocol):
    def add_many(self, rows: list[ImportRow]) -> list[ImportRow]: ...

    def list_by_batch(self, organization_id: UUID, batch_id: UUID) -> list[ImportRow]: ...

    def get_by_id(
        self, organization_id: UUID, batch_id: UUID, row_id: UUID
    ) -> ImportRow | None: ...

    def update(self, row: ImportRow) -> ImportRow: ...

    def update_many(self, rows: list[ImportRow]) -> None: ...

from uuid import UUID

from app.modules.imports.application.commands import GetImportBatchQuery, ImportBatchResult
from app.modules.imports.application.mappers import batch_to_result
from app.modules.imports.domain.exceptions import ImportBatchNotFoundError
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository


class GetImportBatchUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository

    def execute(self, query: GetImportBatchQuery) -> ImportBatchResult:
        batch = self._batch_repository.get_by_id(query.organization_id, query.batch_id)
        if batch is None:
            raise ImportBatchNotFoundError("Import batch not found")

        rows = self._row_repository.list_by_batch(query.organization_id, query.batch_id)
        return batch_to_result(batch, rows)

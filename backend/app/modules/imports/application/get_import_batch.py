from uuid import UUID

from app.modules.fairs.domain.ports import FairRepository
from app.modules.imports.application.batch_display_metadata import resolve_fair_name
from app.modules.imports.application.commands import GetImportBatchQuery, ImportBatchResult
from app.modules.imports.application.mappers import batch_to_result
from app.modules.imports.domain.exceptions import ImportBatchNotFoundError
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository


class GetImportBatchUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
        fair_repository: FairRepository,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
        self._fair_repository = fair_repository

    def execute(self, query: GetImportBatchQuery) -> ImportBatchResult:
        batch = self._batch_repository.get_by_id(query.organization_id, query.batch_id)
        if batch is None:
            raise ImportBatchNotFoundError("Import batch not found")

        rows = self._row_repository.list_by_batch(query.organization_id, query.batch_id)
        fair_name = resolve_fair_name(
            self._fair_repository,
            organization_id=query.organization_id,
            fair_id=batch.fair_id,
        )
        return batch_to_result(batch, rows, fair_name=fair_name)

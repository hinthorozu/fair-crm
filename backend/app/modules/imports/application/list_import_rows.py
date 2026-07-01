from uuid import UUID

from app.modules.customers.domain.ports import CustomerRepository
from app.modules.imports.application.commands import ImportRowListResult, ListImportRowsQuery
from app.modules.imports.application.mappers import row_to_result
from app.modules.imports.domain.exceptions import ImportBatchNotFoundError
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository


class ListImportRowsUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
        customer_repository: CustomerRepository,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
        self._customer_repository = customer_repository

    def execute(self, query: ListImportRowsQuery) -> ImportRowListResult:
        batch = self._batch_repository.get_by_id(query.organization_id, query.batch_id)
        if batch is None:
            raise ImportBatchNotFoundError("Import batch not found")

        rows = self._row_repository.list_by_batch(query.organization_id, query.batch_id)
        customer_names: dict[UUID, str] = {}
        for row in rows:
            if row.match_customer_id and row.match_customer_id not in customer_names:
                customer = self._customer_repository.get_by_id(
                    query.organization_id, row.match_customer_id
                )
                if customer:
                    customer_names[row.match_customer_id] = customer.display_name

        items = [
            row_to_result(
                row,
                match_customer_name=customer_names.get(row.match_customer_id)
                if row.match_customer_id
                else None,
            )
            for row in rows
        ]
        return ImportRowListResult(items=items, total=len(items))

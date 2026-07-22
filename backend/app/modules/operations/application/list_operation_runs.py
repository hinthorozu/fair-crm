from app.modules.operations.application.commands import ListOperationRunsQuery, OperationRunResult
from app.modules.operations.application.mappers import run_to_result
from app.modules.operations.domain.exceptions import OperationNotFoundError
from app.modules.operations.domain.ports import (
    OperationRepository,
    OperationRunListResult,
    OperationRunRepository,
)


class ListOperationRunsUseCase:
    def __init__(
        self,
        operation_repository: OperationRepository,
        run_repository: OperationRunRepository,
    ) -> None:
        self._operation_repository = operation_repository
        self._run_repository = run_repository

    def execute(
        self, query: ListOperationRunsQuery
    ) -> tuple[list[OperationRunResult], OperationRunListResult]:
        operation = self._operation_repository.get_by_id(
            query.organization_id, query.operation_id
        )
        if operation is None:
            raise OperationNotFoundError("Operation not found")

        page = self._run_repository.list_by_operation(
            query.organization_id,
            query.operation_id,
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_dir=query.sort_dir,
        )
        return [run_to_result(run) for run in page.items], page

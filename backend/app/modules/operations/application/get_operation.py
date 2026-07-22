from app.modules.operations.application.commands import GetOperationQuery, OperationDetailResult
from app.modules.operations.application.mappers import operation_to_result, run_to_result
from app.modules.operations.domain.exceptions import OperationNotFoundError
from app.modules.operations.domain.handler_registry import InMemoryHandlerRegistry
from app.modules.operations.domain.ports import OperationRepository, OperationRunRepository


class GetOperationUseCase:
    def __init__(
        self,
        operation_repository: OperationRepository,
        run_repository: OperationRunRepository,
        handler_registry: InMemoryHandlerRegistry,
    ) -> None:
        self._operation_repository = operation_repository
        self._run_repository = run_repository
        self._handler_registry = handler_registry

    def execute(self, query: GetOperationQuery) -> OperationDetailResult:
        operation = self._operation_repository.get_by_id(
            query.organization_id, query.operation_id
        )
        if operation is None:
            raise OperationNotFoundError("Operation not found")

        handler = self._handler_registry.get(operation.operation_type)
        runs_page = self._run_repository.list_by_operation(
            query.organization_id,
            operation.id,
            page=1,
            page_size=50,
            sort_by="created_at",
            sort_dir="desc",
        )
        latest_run = None
        if operation.latest_run_id:
            latest_run = self._run_repository.get_by_id(
                query.organization_id, operation.latest_run_id
            )

        return OperationDetailResult(
            operation=operation_to_result(
                operation, handler=handler, latest_run=latest_run
            ),
            runs=[run_to_result(run) for run in runs_page.items],
        )

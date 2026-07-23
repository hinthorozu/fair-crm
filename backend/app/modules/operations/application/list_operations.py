from app.modules.operations.application.commands import ListOperationsQuery, OperationResult
from app.modules.operations.application.mappers import operation_to_result
from app.modules.operations.domain.handler_registry import InMemoryHandlerRegistry
from app.modules.operations.domain.ports import (
    OperationListResult,
    OperationRepository,
    OperationRunRepository,
)


class ListOperationsUseCase:
    def __init__(
        self,
        operation_repository: OperationRepository,
        handler_registry: InMemoryHandlerRegistry,
        run_repository: OperationRunRepository | None = None,
    ) -> None:
        self._operation_repository = operation_repository
        self._handler_registry = handler_registry
        self._run_repository = run_repository

    def execute(self, query: ListOperationsQuery) -> tuple[list[OperationResult], OperationListResult]:
        page = self._operation_repository.list_by_organization(
            query.organization_id,
            operation_type=query.operation_type,
            status=query.status,
            search=query.search,
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_dir=query.sort_dir,
        )
        latest_by_id: dict = {}
        if self._run_repository is not None:
            run_ids = [
                operation.latest_run_id
                for operation in page.items
                if operation.latest_run_id is not None
            ]
            latest_by_id = self._run_repository.get_by_ids(query.organization_id, run_ids)

        items = [
            operation_to_result(
                operation,
                handler=self._handler_registry.get(operation.operation_type),
                latest_run=(
                    latest_by_id.get(operation.latest_run_id)
                    if operation.latest_run_id is not None
                    else None
                ),
            )
            for operation in page.items
        ]
        return items, page

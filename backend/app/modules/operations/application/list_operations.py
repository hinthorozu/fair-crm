from app.modules.operations.application.commands import ListOperationsQuery, OperationResult
from app.modules.operations.application.mappers import operation_to_result
from app.modules.operations.domain.handler_registry import InMemoryHandlerRegistry
from app.modules.operations.domain.ports import OperationListResult, OperationRepository


class ListOperationsUseCase:
    def __init__(
        self,
        operation_repository: OperationRepository,
        handler_registry: InMemoryHandlerRegistry,
    ) -> None:
        self._operation_repository = operation_repository
        self._handler_registry = handler_registry

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
        items = [
            operation_to_result(
                operation,
                handler=self._handler_registry.get(operation.operation_type),
            )
            for operation in page.items
        ]
        return items, page

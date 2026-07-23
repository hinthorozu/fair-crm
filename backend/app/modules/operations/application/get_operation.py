from sqlalchemy.orm import Session

from app.modules.operations.application.commands import GetOperationQuery, OperationDetailResult
from app.modules.operations.application.mappers import operation_to_result, run_to_result
from app.modules.operations.domain.exceptions import OperationNotFoundError
from app.modules.operations.domain.handler_registry import InMemoryHandlerRegistry
from app.modules.operations.domain.ports import OperationRepository, OperationRunRepository
from app.modules.operations.domain.value_objects import OperationType, RunStatus
from app.modules.operations.infrastructure.handlers.bulk_email_operation_sync import (
    hydrate_run_from_batch,
    resolve_batch_for_operation,
)
from app.modules.operations.infrastructure.handlers.scraper_operation_sync import (
    extract_scraper_run_id,
    hydrate_run_from_scraper_history,
)
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService


class GetOperationUseCase:
    def __init__(
        self,
        operation_repository: OperationRepository,
        run_repository: OperationRunRepository,
        handler_registry: InMemoryHandlerRegistry,
        run_history_service: ScraperRunHistoryService | None = None,
        db: Session | None = None,
    ) -> None:
        self._operation_repository = operation_repository
        self._run_repository = run_repository
        self._handler_registry = handler_registry
        self._run_history_service = run_history_service
        self._db = db

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
        runs = list(runs_page.items)
        if operation.operation_type == OperationType.SCRAPER:
            runs = [self._hydrate_scraper_run(run) for run in runs]
        elif operation.operation_type == OperationType.BULK_EMAIL:
            runs = [self._hydrate_bulk_email_run(operation.organization_id, operation.id, run) for run in runs]

        latest_run = None
        if operation.latest_run_id:
            latest_run = next(
                (run for run in runs if run.id == operation.latest_run_id),
                None,
            )
            if latest_run is None:
                latest_run = self._run_repository.get_by_id(
                    query.organization_id, operation.latest_run_id
                )
                if latest_run is not None and operation.operation_type == OperationType.SCRAPER:
                    latest_run = self._hydrate_scraper_run(latest_run)
                elif latest_run is not None and operation.operation_type == OperationType.BULK_EMAIL:
                    latest_run = self._hydrate_bulk_email_run(
                        operation.organization_id, operation.id, latest_run
                    )

        return OperationDetailResult(
            operation=operation_to_result(
                operation, handler=handler, latest_run=latest_run
            ),
            runs=[run_to_result(run) for run in runs],
        )

    def _hydrate_scraper_run(self, run):
        if self._run_history_service is None:
            return run
        if run.status not in {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.PAUSED}:
            # Still refresh result metadata (import_batch_id) for terminal runs.
            scraper_run_id = extract_scraper_run_id(run)
            if scraper_run_id is None:
                return run
            scraper_run = self._run_history_service.get_run(scraper_run_id)
            if scraper_run is None:
                return run
            return hydrate_run_from_scraper_history(run, scraper_run)

        scraper_run_id = extract_scraper_run_id(run)
        if scraper_run_id is None:
            return run
        scraper_run = self._run_history_service.get_run(scraper_run_id)
        if scraper_run is None:
            return run
        return hydrate_run_from_scraper_history(run, scraper_run)

    def _hydrate_bulk_email_run(self, organization_id, operation_id, run):
        if self._db is None:
            return run
        batch = resolve_batch_for_operation(
            self._db,
            organization_id=organization_id,
            operation_id=operation_id,
            run=run,
        )
        if batch is None:
            return run
        return hydrate_run_from_batch(run, batch)

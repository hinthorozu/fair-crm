from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from app.modules.customers.domain.ports import CustomerRepository
from app.modules.fairs.domain.ports import FairRepository
from app.modules.operations.domain.handler_registry import InMemoryHandlerRegistry
from app.modules.operations.infrastructure.handlers.manual_task_handler import (
    ManualTaskHandler,
)
from app.modules.operations.infrastructure.handlers.scraper_handler import ScraperHandler
from app.modules.todos.domain.ports import TodoRepository

if TYPE_CHECKING:
    from app.modules.scraper.application.fair_scraper_job_runner import FairScraperJobCommand
    from app.modules.scraper.services.scraper_adapter_service import ScraperAdapterService
    from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService


def build_handler_registry(
    *,
    todo_repository: TodoRepository | None = None,
    fair_repository: FairRepository | None = None,
    customer_repository: CustomerRepository | None = None,
    adapter_service: ScraperAdapterService | None = None,
    run_history_service: ScraperRunHistoryService | None = None,
    scraper_job_scheduler: Callable[[FairScraperJobCommand], None] | None = None,
) -> InMemoryHandlerRegistry:
    registry = InMemoryHandlerRegistry()
    registry.register(
        ManualTaskHandler(
            todo_repository=todo_repository,
            fair_repository=fair_repository,
            customer_repository=customer_repository,
        )
    )
    registry.register(
        ScraperHandler(
            fair_repository=fair_repository,
            adapter_service=adapter_service,
            run_history_service=run_history_service,
            job_scheduler=scraper_job_scheduler,
        )
    )
    return registry


def build_default_handler_registry() -> InMemoryHandlerRegistry:
    """Registry without DB wiring — enough for metadata/read paths."""
    return build_handler_registry()


default_handler_registry = build_default_handler_registry()

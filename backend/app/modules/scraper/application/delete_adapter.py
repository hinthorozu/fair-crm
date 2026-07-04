"""Delete adapter with linked fair cleanup and run history removal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.scraper.domain.scraper_adapter_exceptions import AdapterNotFoundError
from app.modules.scraper.services.scraper_adapter_service import ScraperAdapterService
from app.modules.scraper.services.scraper_run_history_service import (
    ScraperRunHistoryService,
    create_run_history_service,
)


@dataclass(frozen=True)
class AdapterDeletePreviewActiveRun:
    id: UUID
    fair_name: str | None
    input_url: str | None
    started_at: datetime


@dataclass(frozen=True)
class AdapterDeletePreview:
    adapter_key: str
    display_name: str
    linked_fairs_count: int
    affected_fairs: tuple[str, ...]
    active_runs_count: int
    active_runs: tuple[AdapterDeletePreviewActiveRun, ...]


class DeleteAdapterUseCase:
    def __init__(
        self,
        session: Session,
        *,
        adapter_service: ScraperAdapterService,
        run_history_service: ScraperRunHistoryService | None = None,
        fair_repository: SqlAlchemyFairRepository | None = None,
    ) -> None:
        self._session = session
        self._adapter_service = adapter_service
        self._run_history_service = run_history_service or create_run_history_service(session)
        self._fair_repository = fair_repository or SqlAlchemyFairRepository(session)

    def get_delete_preview(self, organization_id: UUID, adapter_key: str) -> AdapterDeletePreview:
        view = self._adapter_service.get_adapter(organization_id, adapter_key)
        linked_fairs = self._fair_repository.list_linked_to_adapter(organization_id, adapter_key)
        active_runs = self._run_history_service.list_running_for_adapter(
            adapter_key=view.adapter_key,
            organization_id=organization_id,
        )
        return AdapterDeletePreview(
            adapter_key=view.adapter_key,
            display_name=view.display_name,
            linked_fairs_count=len(linked_fairs),
            affected_fairs=tuple(fair.name for fair in linked_fairs),
            active_runs_count=len(active_runs),
            active_runs=tuple(
                AdapterDeletePreviewActiveRun(
                    id=run.id,
                    fair_name=run.fair_name,
                    input_url=run.input_url,
                    started_at=run.started_at,
                )
                for run in active_runs
            ),
        )

    def execute(self, organization_id: UUID, adapter_key: str) -> None:
        preview = self.get_delete_preview(organization_id, adapter_key)
        now = datetime.now(tz=UTC)

        self._fair_repository.unlink_adapter_key(organization_id, preview.adapter_key, now=now)
        self._run_history_service.hard_delete_runs_for_adapter(
            adapter_key=preview.adapter_key,
            organization_id=organization_id,
        )
        try:
            self._adapter_service.hard_delete_adapter(organization_id, preview.adapter_key)
        except AdapterNotFoundError as exc:
            raise AdapterNotFoundError(f"Adapter not found: {adapter_key}") from exc
        self._session.flush()

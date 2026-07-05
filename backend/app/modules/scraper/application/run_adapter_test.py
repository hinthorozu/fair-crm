"""Start an adapter test scraper run from a user-supplied URL."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.fairs.domain.exceptions import InvalidFairSourceUrlError
from app.modules.fairs.domain.services.normalizers import normalize_source_url
from app.modules.scraper.core.manifest_registry import get_manifest_registry
from app.modules.scraper.domain.adapter_engine import AdapterEngineType
from app.modules.scraper.domain.scraper_run_source import ScraperRunSource
from app.modules.scraper.services.adapter_engine_service import AdapterEngineService, create_adapter_engine_service
from app.modules.scraper.services.adapter_instance_resolver import resolve_engine_key
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService


@dataclass(frozen=True)
class RunAdapterTestCommand:
    organization_id: UUID
    adapter_key: str
    input_url: str


class AdapterNotRegisteredError(LookupError):
    pass


class DynamicAdapterEngineNotRunnableError(ValueError):
    pass


class RunAdapterTestUseCase:
    def __init__(
        self,
        run_history_service: ScraperRunHistoryService,
        session: Session,
        engine_service: AdapterEngineService | None = None,
    ) -> None:
        self._run_history_service = run_history_service
        self._session = session
        self._engine_service = engine_service or create_adapter_engine_service()

    def execute(self, command: RunAdapterTestCommand) -> ScraperRunHistory:
        normalized_key = command.adapter_key.strip().lower()
        engine_key = resolve_engine_key(self._session, command.organization_id, normalized_key)
        engine_type = self._resolve_engine_type(engine_key)
        if engine_type != AdapterEngineType.STATIC:
            raise DynamicAdapterEngineNotRunnableError(
                f"Dynamic adapter engine is not runnable yet: {engine_key}"
            )

        try:
            source_url = normalize_source_url(command.input_url)
        except InvalidFairSourceUrlError as exc:
            raise ValueError(str(exc)) from exc
        if source_url is None:
            raise ValueError("input_url is required")

        return self._run_history_service.start_run(
            adapter_key=normalized_key,
            input_url=source_url,
            fair_name="Adapter Test",
            fair_year=None,
            organization_id=command.organization_id,
            fair_id=None,
            run_source=ScraperRunSource.MANUAL_TEST,
        )

    def _resolve_engine_type(self, engine_key: str) -> AdapterEngineType:
        registry = get_manifest_registry()
        try:
            return registry.get(engine_key.strip().lower()).engine_type
        except KeyError:
            return AdapterEngineType.DYNAMIC

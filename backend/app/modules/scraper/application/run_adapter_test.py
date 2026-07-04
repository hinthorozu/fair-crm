"""Start an adapter test scraper run from a user-supplied URL."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.fairs.domain.exceptions import InvalidFairSourceUrlError
from app.modules.fairs.domain.services.normalizers import normalize_source_url
from app.modules.scraper.core.manifest_registry import ManifestRegistry, get_manifest_registry
from app.modules.scraper.domain.scraper_run_history import ScraperRunHistory
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService


@dataclass(frozen=True)
class RunAdapterTestCommand:
    organization_id: UUID
    adapter_key: str
    input_url: str


class AdapterNotRegisteredError(LookupError):
    pass


class RunAdapterTestUseCase:
    def __init__(
        self,
        run_history_service: ScraperRunHistoryService,
        manifest_registry: ManifestRegistry | None = None,
    ) -> None:
        self._run_history_service = run_history_service
        self._manifest_registry = manifest_registry or get_manifest_registry()

    def execute(self, command: RunAdapterTestCommand) -> ScraperRunHistory:
        normalized_key = command.adapter_key.strip().lower()
        try:
            self._manifest_registry.get(normalized_key)
        except KeyError as exc:
            raise AdapterNotRegisteredError(f"Adapter not found: {command.adapter_key}") from exc

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
        )

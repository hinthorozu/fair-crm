"""Build adapter management dashboard payloads from manifests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.scraper.core.scraper_manager import ScraperManager
from app.modules.scraper.domain.requested_output_fields import (
    REQUESTED_OUTPUT_FIELD_KEYS,
    output_field_capabilities_from_supports,
)
from app.modules.scraper.manifests.scraper_manifest import ScraperManifest

if TYPE_CHECKING:
    from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService


def build_adapter_features(manifest: ScraperManifest) -> list[dict[str, str | bool]]:
    capabilities = output_field_capabilities_from_supports(manifest.supports)
    return [
        {
            "key": key,
            "label": key,
            "enabled": capabilities[key],
        }
        for key in REQUESTED_OUTPUT_FIELD_KEYS
    ]


def resolve_actions_available(manifest: ScraperManifest) -> list[str]:
    actions = ["view"]
    if manifest.supports.list_scraping:
        actions.append("run")
    return actions


def build_dashboard_summary(
    manifests: list[ScraperManifest],
    *,
    last_run_adapter: str | None = None,
    failed_scraper_count: int = 0,
) -> dict[str, int | str | None]:
    return {
        "total_adapters": len(manifests),
        "last_run_adapter": last_run_adapter,
        "failed_scraper_count": failed_scraper_count,
    }


class ScraperDashboardService:
    """Aggregates adapter manifest metadata for the Adapter Management UI."""

    def __init__(
        self,
        manager: ScraperManager,
        run_history_service: "ScraperRunHistoryService | None" = None,
    ) -> None:
        self._manager = manager
        self._run_history_service = run_history_service

    def list_manifests(self) -> list[ScraperManifest]:
        return self._manager.list_manifests()

    def build_summary(self) -> dict[str, int | str | None]:
        manifests = self.list_manifests()
        if self._run_history_service is None:
            return build_dashboard_summary(manifests)
        run_stats = self._run_history_service.get_dashboard_run_stats()
        return build_dashboard_summary(
            manifests,
            last_run_adapter=run_stats["last_run_adapter"],  # type: ignore[arg-type]
            failed_scraper_count=run_stats["failed_scraper_count"],  # type: ignore[arg-type]
        )

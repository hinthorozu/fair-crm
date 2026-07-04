"""Catalog of registered adapter engines (static/dynamic templates)."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.scraper.core.manifest_registry import ManifestRegistry, get_manifest_registry
from app.modules.scraper.domain.adapter_engine import AdapterEngineType
from app.modules.scraper.manifests.scraper_manifest import ScraperManifest
from app.modules.scraper.services.scraper_dashboard_service import (
    build_adapter_features,
    resolve_actions_available,
)


@dataclass(frozen=True)
class AdapterEngineView:
    engine_key: str
    display_name: str
    engine_type: AdapterEngineType
    status: str
    version: str
    features: list[dict[str, str | bool]]
    actions_available: list[str]
    supported_sites: tuple[str, ...]
    is_runnable: bool


class AdapterEngineService:
    def __init__(self, manifest_registry: ManifestRegistry | None = None) -> None:
        self._manifest_registry = manifest_registry or get_manifest_registry()

    def list_engines(self) -> list[AdapterEngineView]:
        return [self._view_from_manifest(manifest) for manifest in self._manifest_registry.list_manifests()]

    def get_engine(self, engine_key: str) -> AdapterEngineView:
        manifest = self._manifest_registry.get(engine_key.strip().lower())
        return self._view_from_manifest(manifest)

    def engine_type_for_key(self, engine_key: str) -> AdapterEngineType:
        return self.get_engine(engine_key).engine_type

    def _view_from_manifest(self, manifest: ScraperManifest) -> AdapterEngineView:
        return AdapterEngineView(
            engine_key=manifest.adapter_key,
            display_name=manifest.display_name,
            engine_type=manifest.engine_type,
            status=manifest.status.value,
            version=manifest.version,
            features=build_adapter_features(manifest),
            actions_available=resolve_actions_available(manifest),
            supported_sites=manifest.supported_sites,
            is_runnable=manifest.engine_type == AdapterEngineType.STATIC,
        )


def create_adapter_engine_service(
    manifest_registry: ManifestRegistry | None = None,
) -> AdapterEngineService:
    return AdapterEngineService(manifest_registry)

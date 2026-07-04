"""Registry for declarative scraper adapter manifests."""

from __future__ import annotations

from app.modules.scraper.manifests.scraper_manifest import ScraperManifest


class ManifestRegistry:
    def __init__(self) -> None:
        self._manifests: dict[str, ScraperManifest] = {}

    def register(self, manifest: ScraperManifest) -> None:
        key = manifest.adapter_key.strip().lower()
        if not key:
            raise ValueError("Manifest adapter_key must not be empty")
        self._manifests[key] = manifest

    def get(self, adapter_key: str) -> ScraperManifest:
        key = adapter_key.strip().lower()
        manifest = self._manifests.get(key)
        if manifest is None:
            registered = ", ".join(sorted(self._manifests)) or "(none)"
            raise KeyError(
                f"No scraper manifest registered for adapter_key={adapter_key!r}. Registered: {registered}"
            )
        return manifest

    def list_adapter_keys(self) -> list[str]:
        return sorted(self._manifests.keys())

    def list_manifests(self) -> list[ScraperManifest]:
        return [self._manifests[key] for key in self.list_adapter_keys()]


_default_manifest_registry: ManifestRegistry | None = None


def get_manifest_registry() -> ManifestRegistry:
    global _default_manifest_registry
    if _default_manifest_registry is None:
        from app.modules.scraper.manifests import register_builtin_manifests

        _default_manifest_registry = ManifestRegistry()
        register_builtin_manifests(_default_manifest_registry)
    return _default_manifest_registry

"""Adapter registry for dependency injection."""

from app.modules.scraper.core.interfaces import IScraperAdapter


class ScraperAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, IScraperAdapter] = {}

    def register(self, adapter: IScraperAdapter) -> None:
        key = adapter.site_key.strip().lower()
        if not key:
            raise ValueError("Adapter site_key must not be empty")
        self._adapters[key] = adapter

    def get(self, site_key: str) -> IScraperAdapter:
        key = site_key.strip().lower()
        adapter = self._adapters.get(key)
        if adapter is None:
            registered = ", ".join(sorted(self._adapters)) or "(none)"
            raise KeyError(f"No scraper adapter registered for site_key={site_key!r}. Registered: {registered}")
        return adapter

    def list_site_keys(self) -> list[str]:
        return sorted(self._adapters.keys())

    def list_adapters(self) -> list[IScraperAdapter]:
        return [self._adapters[key] for key in self.list_site_keys()]


_default_registry: ScraperAdapterRegistry | None = None


def get_scraper_adapter_registry() -> ScraperAdapterRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = ScraperAdapterRegistry()
    return _default_registry

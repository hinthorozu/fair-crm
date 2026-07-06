"""Site-specific scraper adapters (TÜYAP, IFM, Hannover, Canton, …).

Each adapter implements ``IScraperAdapter`` and is registered in
``ScraperAdapterRegistry`` at application startup.
"""

from app.modules.scraper.adapters.customer_contact_enrichment_adapter import (
    CustomerContactEnrichmentAdapter,
)
from app.modules.scraper.adapters.tuyap_new_adapter import TuyapNewAdapter
from app.modules.scraper.adapters.tuyap_old_adapter import TuyapOldAdapter
from app.modules.scraper.core.browser_service import BrowserService
from app.modules.scraper.core.scraper_registry import ScraperAdapterRegistry

_BUILTIN_ADAPTERS: tuple[type, ...] = (
    TuyapOldAdapter,
    TuyapNewAdapter,
    CustomerContactEnrichmentAdapter,
)


def register_builtin_adapters(
    registry: ScraperAdapterRegistry,
    *,
    browser: BrowserService | None = None,
) -> None:
    for adapter_cls in _BUILTIN_ADAPTERS:
        registry.register(adapter_cls(browser=browser))


__all__ = [
    "CustomerContactEnrichmentAdapter",
    "TuyapNewAdapter",
    "TuyapOldAdapter",
    "register_builtin_adapters",
]

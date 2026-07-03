from app.modules.scraper.core.interfaces import IScraperAdapter
from app.modules.scraper.core.scraper_manager import ScraperManager
from app.modules.scraper.core.scraper_registry import ScraperAdapterRegistry, get_scraper_adapter_registry

__all__ = [
    "IScraperAdapter",
    "ScraperAdapterRegistry",
    "ScraperManager",
    "get_scraper_adapter_registry",
]

"""FastAPI dependency injection for the Exhibitor Scraper module."""

from functools import lru_cache

from app.modules.scraper.core.scraper_manager import ScraperManager
from app.modules.scraper.core.scraper_registry import ScraperAdapterRegistry, get_scraper_adapter_registry
from app.modules.scraper.normalizers.company_normalizer import CompanyNormalizer
from app.modules.scraper.services.scraper_service import ScraperService


@lru_cache
def get_company_normalizer() -> CompanyNormalizer:
    return CompanyNormalizer()


def get_scraper_manager(
    registry: ScraperAdapterRegistry | None = None,
    normalizer: CompanyNormalizer | None = None,
) -> ScraperManager:
    return ScraperManager(
        registry=registry or get_scraper_adapter_registry(),
        normalizer=normalizer or get_company_normalizer(),
    )


def get_scraper_service(
    manager: ScraperManager | None = None,
) -> ScraperService:
    return ScraperService(manager or get_scraper_manager())

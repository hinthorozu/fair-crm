"""Facade over ``ScraperManager`` for future API and background jobs."""

from app.modules.scraper.core.scraper_manager import ScraperManager
from app.modules.scraper.jobs.scraper_job import ScraperJob
from app.modules.scraper.types.scraper_context import ScraperContext
from app.modules.scraper.types.scraper_result import ScraperResult


class ScraperService:
    def __init__(self, manager: ScraperManager) -> None:
        self._manager = manager

    def list_sites(self) -> list[str]:
        return self._manager.list_site_keys()

    def scrape(self, site_key: str, context: ScraperContext) -> ScraperResult:
        return self._manager.run(site_key, context)

    def enqueue(self, site_key: str, context: ScraperContext) -> ScraperJob:
        return self._manager.create_job(site_key, context)

    def run_job(self, job: ScraperJob) -> ScraperJob:
        return self._manager.execute_job(job)

"""Orchestrates adapter selection, scraping, and normalization."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.scraper.core.interfaces import IScraperAdapter
from app.modules.scraper.core.scraper_registry import ScraperAdapterRegistry
from app.modules.scraper.dto.normalized_company_dto import NormalizedCompanyDto
from app.modules.scraper.jobs.scraper_job import ScraperJob, ScraperJobStatus
from app.modules.scraper.normalizers.company_normalizer import CompanyNormalizer
from app.modules.scraper.types.scraper_context import ScraperContext
from app.modules.scraper.types.scraper_result import ScraperResult


class ScraperManager:
    """Coordinates scraper adapters and normalization.

    Inject ``ScraperAdapterRegistry`` and ``CompanyNormalizer`` via constructor
    (see ``app.modules.scraper.api.dependencies``).
    """

    def __init__(
        self,
        registry: ScraperAdapterRegistry,
        normalizer: CompanyNormalizer,
    ) -> None:
        self._registry = registry
        self._normalizer = normalizer

    def register(self, adapter: IScraperAdapter) -> None:
        self._registry.register(adapter)

    def list_site_keys(self) -> list[str]:
        return self._registry.list_site_keys()

    def run(self, site_key: str, context: ScraperContext) -> ScraperResult:
        adapter = self._registry.get(site_key)
        raw_rows = adapter.scrape(context)
        normalized, warnings = self._normalizer.normalize_many(raw_rows)
        return ScraperResult(
            site_key=adapter.site_key,
            fair_id=context.fair_id,
            companies=normalized,
            raw_count=len(raw_rows),
            normalized_count=len(normalized),
            errors=[],
            warnings=warnings,
            metadata={"adapter": adapter.display_name, **context.metadata},
            scraped_at=datetime.now(UTC),
        )

    def create_job(self, site_key: str, context: ScraperContext) -> ScraperJob:
        self._registry.get(site_key)
        return ScraperJob(
            id=uuid4(),
            site_key=site_key.strip().lower(),
            status=ScraperJobStatus.PENDING,
            context=context,
            created_at=datetime.now(UTC),
        )

    def execute_job(self, job: ScraperJob) -> ScraperJob:
        started = datetime.now(UTC)
        running = ScraperJob(
            id=job.id,
            site_key=job.site_key,
            status=ScraperJobStatus.RUNNING,
            context=job.context,
            result=None,
            error_message=None,
            created_at=job.created_at,
            started_at=started,
            completed_at=None,
        )
        try:
            result = self.run(job.site_key, job.context)
        except Exception as exc:
            return ScraperJob(
                id=job.id,
                site_key=job.site_key,
                status=ScraperJobStatus.FAILED,
                context=job.context,
                result=None,
                error_message=str(exc),
                created_at=job.created_at,
                started_at=started,
                completed_at=datetime.now(UTC),
            )
        return ScraperJob(
            id=job.id,
            site_key=job.site_key,
            status=ScraperJobStatus.COMPLETED,
            context=job.context,
            result=result,
            error_message=None,
            created_at=job.created_at,
            started_at=started,
            completed_at=datetime.now(UTC),
        )

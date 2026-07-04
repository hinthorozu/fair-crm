"""Orchestrates adapter selection, scraping, and normalization."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.scraper.core.browser_service import BrowserService
from app.modules.scraper.core.interfaces import IScraperAdapter
from app.modules.scraper.core.manifest_registry import ManifestRegistry, get_manifest_registry
from app.modules.scraper.core.scraper_registry import ScraperAdapterRegistry
from app.modules.scraper.manifests.scraper_manifest import ScraperManifest
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
        browser_service: BrowserService | None = None,
        manifest_registry: ManifestRegistry | None = None,
    ) -> None:
        self._registry = registry
        self._normalizer = normalizer
        self._browser_service = browser_service
        self._manifest_registry = manifest_registry or get_manifest_registry()

    @property
    def browser_service(self) -> BrowserService | None:
        return self._browser_service

    def register(self, adapter: IScraperAdapter) -> None:
        self._registry.register(adapter)

    def list_site_keys(self) -> list[str]:
        return self._registry.list_site_keys()

    def list_manifests(self) -> list[ScraperManifest]:
        return self._manifest_registry.list_manifests()

    def get_manifest(self, adapter_key: str) -> ScraperManifest:
        return self._manifest_registry.get(adapter_key)

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

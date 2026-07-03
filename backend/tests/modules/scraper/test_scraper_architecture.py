"""Architecture tests for Exhibitor Scraper module."""

from uuid import uuid4

import pytest

from app.modules.scraper.core.scraper_manager import ScraperManager
from app.modules.scraper.core.scraper_registry import ScraperAdapterRegistry
from app.modules.scraper.dto.raw_company_dto import RawCompanyDto
from app.modules.scraper.jobs.scraper_job import ScraperJobStatus
from app.modules.scraper.normalizers.company_normalizer import CompanyNormalizer
from app.modules.scraper.types.scraper_context import ScraperContext


class _StubAdapter:
    site_key = "demo"
    display_name = "Demo Fair"

    def scrape(self, context: ScraperContext) -> list[RawCompanyDto]:
        return [
            RawCompanyDto(
                company_name="  Demo Exhibitor AS  ",
                hall="3",
                stand="A12",
                email="info@demo.test",
                source_url=context.list_url,
            )
        ]


def test_company_normalizer_produces_canonical_row():
    normalizer = CompanyNormalizer()
    normalized = normalizer.normalize(RawCompanyDto(company_name="Acme Ltd", hall="1", stand="B2"))
    assert normalized is not None
    row = normalized.to_canonical_row()
    assert row["company_name"] == "Acme Ltd"
    assert row["hall"] == "1"
    assert row["stand"] == "B2"


def test_scraper_manager_run_with_registered_adapter():
    registry = ScraperAdapterRegistry()
    registry.register(_StubAdapter())
    manager = ScraperManager(registry, CompanyNormalizer())

    result = manager.run("demo", ScraperContext(fair_id=uuid4(), list_url="https://example.test/list"))

    assert result.site_key == "demo"
    assert result.raw_count == 1
    assert result.normalized_count == 1
    assert result.companies[0].company_name == "Demo Exhibitor AS"
    assert result.to_canonical_rows()[0]["email"] == "info@demo.test"


def test_scraper_manager_execute_job_success():
    registry = ScraperAdapterRegistry()
    registry.register(_StubAdapter())
    manager = ScraperManager(registry, CompanyNormalizer())
    job = manager.create_job("demo", ScraperContext(list_url="https://example.test/list"))

    completed = manager.execute_job(job)

    assert completed.status == ScraperJobStatus.COMPLETED
    assert completed.result is not None
    assert completed.result.normalized_count == 1


def test_scraper_manager_unknown_site_raises():
    manager = ScraperManager(ScraperAdapterRegistry(), CompanyNormalizer())
    with pytest.raises(KeyError, match="No scraper adapter"):
        manager.run("unknown", ScraperContext())

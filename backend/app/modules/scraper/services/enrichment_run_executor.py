"""Execute customer contact enrichment and build import handoff."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.scraper.core.scraper_run_logger import ScraperRunLogger
from app.modules.scraper.domain.requested_output_fields import filter_handoff_by_requested_fields
from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto
from app.modules.scraper.dto.raw_company_dto import RawCompanyDto
from app.modules.scraper.exporters.enrichment_handoff_mapper import enrichment_results_to_raw_companies
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportExporter, ScraperImportHandoff
from app.modules.scraper.normalizers.company_normalizer import CompanyNormalizer
from app.modules.scraper.services.customer_contact_enrichment_service import enrich_customer_website
from app.modules.scraper.services.enrichment_candidate_service import (
    EnrichmentCandidate,
    list_enrichment_candidates,
)
from app.modules.scraper.services.enrichment_customer_run_logger import EnrichmentCustomerRunLogger
from app.modules.scraper.types.scraper_result import ScraperResult
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def build_handoff_from_enrichment_results(
    raw_rows: list[RawCompanyDto],
    *,
    requested_fields: list[str],
    adapter_key: str = ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
) -> ScraperImportHandoff:
    normalizer = CompanyNormalizer()
    normalized, _warnings = normalizer.normalize_many(raw_rows)
    result = ScraperResult(
        site_key=adapter_key,
        fair_id=None,
        companies=normalized,
        raw_count=len(raw_rows),
        normalized_count=len(normalized),
        errors=[],
        warnings=[],
        metadata={"adapter": "Müşteri İletişim Zenginleştirme"},
        scraped_at=datetime.now(UTC),
    )
    handoff = ScraperImportExporter().export(
        result,
        fair_name="Müşteri İletişim Zenginleştirme",
        fair_year=None,
        source_url=None,
    )
    return filter_handoff_by_requested_fields(handoff, requested_fields)


def execute_enrichment_run(
    session: Session,
    organization_id: UUID,
    *,
    run_id: UUID | None = None,
    run_logger: ScraperRunLogger | None = None,
    limit: int | None = None,
    requested_fields: list[str],
    max_pages: int = 10,
    fetcher: Callable[[str], str] | None = None,
) -> tuple[list[EnrichmentResultDto], ScraperImportHandoff]:
    candidates = list_enrichment_candidates(session, organization_id, limit=limit)
    results: list[EnrichmentResultDto] = []
    for candidate in candidates:
        results.append(
            enrich_customer_website(
                candidate,
                requested_fields=requested_fields,
                max_pages=max_pages,
                fetcher=fetcher,
                run_id=run_id,
                run_logger=run_logger,
            )
        )

    raw_rows = enrichment_results_to_raw_companies(results, requested_fields=requested_fields)
    handoff = build_handoff_from_enrichment_results(
        raw_rows,
        requested_fields=requested_fields,
    )

    if run_logger is not None and run_id is not None:
        raw_by_customer = {
            str(row.metadata.get("customer_id")): row
            for row in raw_rows
            if row.metadata and row.metadata.get("customer_id")
        }
        for result in results:
            event_logger = EnrichmentCustomerRunLogger(
                run_logger,
                run_id=run_id,
                candidate=EnrichmentCandidate(
                    customer_id=result.customer_id,
                    company_name=result.company_name,
                    website=result.website,
                ),
            )
            raw_row = raw_by_customer.get(str(result.customer_id))
            if raw_row is not None:
                event_logger.handoff_row_created(
                    source_url=str(raw_row.metadata.get("source_url") or result.website),
                )
            elif result.status == "found":
                event_logger.handoff_row_skipped(reason="handoff_filter_empty")
            else:
                event_logger.handoff_row_skipped(reason=result.status)

    return results, handoff

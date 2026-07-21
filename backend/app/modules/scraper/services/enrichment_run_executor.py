"""Execute customer contact enrichment and build import handoff."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
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
    CompanyNameMatchMode,
    EnrichmentCandidate,
    list_enrichment_candidates,
)
from app.modules.scraper.services.customer_enrichment_state_service import record_scan_result
from app.modules.scraper.services.enrichment_customer_run_logger import EnrichmentCustomerRunLogger
from app.modules.scraper.services.enrichment_run_candidate_preview_logger import (
    log_bulk_enrichment_candidate_preview,
    log_customer_scan_finished,
    log_customer_scan_started,
)
from app.modules.scraper.services.scraper_run_cancellation import RunCancelChecker
from app.modules.scraper.types.scraper_result import ScraperResult
from app.modules.scraper.types.scraper_site import ScraperSiteKey

logger = logging.getLogger(__name__)

CANDIDATES_QUERY_SLOW_WARNING_MS = 10_000
_VALID_COMPANY_NAME_MATCH = frozenset({"contains", "starts_with"})


@dataclass(frozen=True)
class EnrichmentRunExecution:
    results: list[EnrichmentResultDto]
    handoff: ScraperImportHandoff
    cancelled: bool = False
    processed_count: int = 0
    total_candidates: int = 0
    last_processed_customer_id: UUID | None = None


def build_handoff_from_enrichment_results(
    raw_rows: list[RawCompanyDto],
    *,
    requested_fields: list[str],
    adapter_key: str = ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
    fair_id: UUID | None = None,
) -> ScraperImportHandoff:
    normalizer = CompanyNormalizer()
    normalized, _warnings = normalizer.normalize_many(raw_rows)
    result = ScraperResult(
        site_key=adapter_key,
        fair_id=fair_id,
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
    customer_ids: list[UUID] | None = None,
    fair_id: UUID | None = None,
    ignore_previous_scan_state: bool = False,
    include_existing_email: bool = False,
    company_name: str | None = None,
    company_name_match: CompanyNameMatchMode | str = "contains",
    address_contains: str | None = None,
    cancel_checker: RunCancelChecker | None = None,
) -> EnrichmentRunExecution:
    def _cancelled_execution(
        results: list[EnrichmentResultDto],
        *,
        total_candidates: int,
        last_processed_customer_id: UUID | None,
    ) -> EnrichmentRunExecution:
        raw_rows = enrichment_results_to_raw_companies(results, requested_fields=requested_fields)
        handoff = build_handoff_from_enrichment_results(
            raw_rows,
            requested_fields=requested_fields,
            fair_id=fair_id,
        )
        return EnrichmentRunExecution(
            results=results,
            handoff=handoff,
            cancelled=True,
            processed_count=len(results),
            total_candidates=total_candidates,
            last_processed_customer_id=last_processed_customer_id,
        )

    match_mode: CompanyNameMatchMode = (
        company_name_match if company_name_match in _VALID_COMPANY_NAME_MATCH else "contains"
    )
    query_started_at = time.perf_counter()
    if fair_id is not None:
        candidates = list_enrichment_candidates(
            session,
            organization_id,
            limit=limit,
            fair_id=fair_id,
            ignore_previous_scan_state=ignore_previous_scan_state,
            include_existing_email=include_existing_email,
            company_name=company_name,
            company_name_match=match_mode,
            address_contains=address_contains,
        )
    elif customer_ids:
        from app.modules.scraper.services.single_customer_enrichment_service import (
            list_enrichment_candidates_for_customer_ids,
        )

        candidates = list_enrichment_candidates_for_customer_ids(
            session,
            organization_id,
            customer_ids,
        )
    else:
        candidates = list_enrichment_candidates(
            session,
            organization_id,
            limit=limit,
            include_existing_email=include_existing_email,
            company_name=company_name,
            company_name_match=match_mode,
            address_contains=address_contains,
        )
    duration_ms = int((time.perf_counter() - query_started_at) * 1000)
    candidate_count = len(candidates)
    if run_logger is not None:
        finished_metadata = {
            "duration_ms": duration_ms,
            "candidates_count": candidate_count,
            "limit": limit,
            "customer_ids_filter": [str(item) for item in customer_ids or []],
            "fair_id": str(fair_id) if fair_id is not None else None,
            "ignore_previous_scan_state": ignore_previous_scan_state,
            "include_existing_email": include_existing_email,
            "company_name": company_name,
            "company_name_match": match_mode,
            "address_contains": address_contains,
        }
        run_logger.info(
            "candidates_query_finished",
            f"Aday sorgusu tamamlandı ({duration_ms} ms, {candidate_count} aday)",
            metadata=finished_metadata,
        )
        if duration_ms >= CANDIDATES_QUERY_SLOW_WARNING_MS:
            run_logger.warning(
                "candidates_query_slow",
                f"Aday sorgusu beklenenden uzun sürdü ({duration_ms} ms)",
                metadata=finished_metadata,
            )
        run_logger.info(
            "candidates_loaded",
            f"{candidate_count} aday müşteri bulundu",
            metadata={"candidate_count": candidate_count, "limit": limit, "duration_ms": duration_ms},
        )
    elif duration_ms >= CANDIDATES_QUERY_SLOW_WARNING_MS:
        logger.warning(
            "Enrichment candidate query slow org=%s duration_ms=%s candidates=%s",
            organization_id,
            duration_ms,
            candidate_count,
        )

    if cancel_checker is not None and cancel_checker.is_cancel_requested():
        return _cancelled_execution([], total_candidates=candidate_count, last_processed_customer_id=None)

    is_bulk_enrichment_run = customer_ids is None
    if run_logger is not None and is_bulk_enrichment_run:
        log_bulk_enrichment_candidate_preview(run_logger, candidates)

    results: list[EnrichmentResultDto] = []
    last_processed_customer_id: UUID | None = None
    for candidate in candidates:
        if cancel_checker is not None and cancel_checker.is_cancel_requested():
            break
        if run_logger is not None and is_bulk_enrichment_run:
            log_customer_scan_started(run_logger, candidate)
        result = enrich_customer_website(
            candidate,
            requested_fields=requested_fields,
            max_pages=max_pages,
            fetcher=fetcher,
            run_id=run_id,
            run_logger=run_logger,
        )
        if run_logger is not None and is_bulk_enrichment_run:
            log_customer_scan_finished(run_logger, candidate)
        results.append(result)
        last_processed_customer_id = candidate.customer_id
        if run_id is not None:
            record_scan_result(
                session,
                organization_id=organization_id,
                run_id=run_id,
                result=result,
            )
        if cancel_checker is not None and cancel_checker.is_cancel_requested():
            break

    cancelled = cancel_checker is not None and cancel_checker.is_cancel_requested()
    raw_rows = enrichment_results_to_raw_companies(results, requested_fields=requested_fields)
    handoff = build_handoff_from_enrichment_results(
        raw_rows,
        requested_fields=requested_fields,
        fair_id=fair_id,
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

    return EnrichmentRunExecution(
        results=results,
        handoff=handoff,
        cancelled=cancelled,
        processed_count=len(results),
        total_candidates=candidate_count,
        last_processed_customer_id=last_processed_customer_id,
    )

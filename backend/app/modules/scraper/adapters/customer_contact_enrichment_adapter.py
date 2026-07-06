"""Customer website contact enrichment adapter."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.scraper.core.browser_service import BrowserService
from app.modules.scraper.core.scraper_run_logger import ScraperRunLogger, resolve_run_logger
from app.modules.scraper.domain.enrichment_adapter import DEFAULT_ENRICHMENT_REQUESTED_FIELDS
from app.modules.scraper.domain.requested_output_fields import normalize_requested_fields
from app.modules.scraper.dto.raw_company_dto import RawCompanyDto
from app.modules.scraper.exporters.enrichment_handoff_mapper import enrichment_results_to_raw_companies
from app.modules.scraper.services.customer_contact_enrichment_service import enrich_customer_website
from app.modules.scraper.services.enrichment_candidate_service import (
    EnrichmentCandidate,
    list_enrichment_candidates,
)
from app.modules.scraper.types.scraper_context import ScraperContext
from app.modules.scraper.types.scraper_site import ScraperSiteKey

logger = logging.getLogger(__name__)


class CustomerContactEnrichmentAdapter:
    """Enriches existing CRM customers by reading contact data from their websites."""

    def __init__(self, browser: BrowserService | None = None) -> None:
        self._browser = browser

    @property
    def site_key(self) -> str:
        return ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT

    @property
    def display_name(self) -> str:
        return "Müşteri İletişim Zenginleştirme"

    def scrape(self, context: ScraperContext) -> list[RawCompanyDto]:
        return asyncio.run(self.scrape_async(context))

    async def scrape_async(self, context: ScraperContext) -> list[RawCompanyDto]:
        run_log = resolve_run_logger(context)
        requested_fields = self._resolve_requested_fields(context)
        max_pages = int(context.options.get("max_pages") or 10)
        limit = context.options.get("limit")
        limit_value = int(limit) if limit is not None else None

        candidates = self._resolve_candidates(context, limit=limit_value)
        if not candidates:
            run_log.info("enrichment_candidates", "Uygun müşteri bulunamadı")
            return []

        run_log.info(
            "enrichment_candidates",
            f"{len(candidates)} müşteri zenginleştirmeye alındı",
            metadata={"candidate_count": len(candidates)},
        )

        fetcher = context.options.get("fetcher")
        results = []
        for candidate in candidates:
            result = enrich_customer_website(
                candidate,
                requested_fields=requested_fields,
                max_pages=max_pages,
                fetcher=fetcher,
            )
            results.append(result)
            if result.status == "found":
                run_log.info(
                    "enrichment_customer_found",
                    f"İletişim bulundu: {candidate.company_name}",
                    metadata=result.to_summary_dict(),
                )
            elif result.status == "failed":
                run_log.warning(
                    "enrichment_customer_failed",
                    f"Zenginleştirme başarısız: {candidate.company_name}",
                    metadata=result.to_summary_dict(),
                )
            else:
                run_log.info(
                    "enrichment_customer_not_found",
                    f"İletişim bulunamadı: {candidate.company_name}",
                    metadata=result.to_summary_dict(),
                )

        return enrichment_results_to_raw_companies(results, requested_fields=requested_fields)

    def _resolve_requested_fields(self, context: ScraperContext) -> list[str]:
        raw = context.options.get("requested_fields")
        if isinstance(raw, (list, tuple)):
            normalized = normalize_requested_fields(list(raw))
            if normalized:
                return normalized
        return list(DEFAULT_ENRICHMENT_REQUESTED_FIELDS)

    def _resolve_candidates(
        self,
        context: ScraperContext,
        *,
        limit: int | None,
    ) -> list[EnrichmentCandidate]:
        explicit = context.options.get("enrichment_candidates")
        if isinstance(explicit, list) and explicit:
            return [
                EnrichmentCandidate(
                    customer_id=UUID(str(item["customer_id"])),
                    company_name=str(item["company_name"]),
                    website=str(item["website"]),
                )
                for item in explicit
            ]

        organization_id = context.metadata.get("organization_id") or context.options.get("organization_id")
        session = context.options.get("db_session")
        if organization_id is None or session is None or not isinstance(session, Session):
            logger.info("CustomerContactEnrichmentAdapter: organization_id or db_session missing")
            return []

        return list_enrichment_candidates(
            session,
            UUID(str(organization_id)),
            limit=limit,
        )

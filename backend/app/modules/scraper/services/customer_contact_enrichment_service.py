"""Orchestrate website crawl and contact extraction for one customer."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from app.modules.scraper.core.scraper_run_logger import ScraperRunLogger
from app.modules.scraper.crawlers.website_contact_crawler import crawl_customer_website
from app.modules.scraper.domain.enrichment_adapter import ENRICHMENT_REQUESTED_FIELD_KEYS
from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto, SourcedValue
from app.modules.scraper.extractors.contact_extractor import extract_contacts_from_html
from app.modules.scraper.fetchers.website_http_fetcher import fetch_html_with_status
from app.modules.scraper.services.enrichment_candidate_service import EnrichmentCandidate
from app.modules.scraper.services.enrichment_customer_run_logger import EnrichmentCustomerRunLogger


def _merge_sourced_values(
    current: list[SourcedValue],
    incoming: list[SourcedValue],
) -> list[SourcedValue]:
    seen = {item.value.lower() for item in current}
    merged = list(current)
    for item in incoming:
        key = item.value.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def _has_requested_data(result: EnrichmentResultDto, requested_fields: set[str]) -> bool:
    if "email" in requested_fields and result.emails:
        return True
    if "phone" in requested_fields and result.phones:
        return True
    if "address" in requested_fields and result.address is not None:
        return True
    for key in ("instagram", "facebook", "linkedin", "youtube"):
        if key in requested_fields and result.social_links.get(key) is not None:
            return True
    return False


def _build_logging_fetcher(event_logger: EnrichmentCustomerRunLogger) -> Callable[[str], str]:
    def fetch(url: str) -> str:
        event_logger.website_fetch_started(url)
        result = fetch_html_with_status(url)
        if result.html is None:
            event_logger.website_fetch_failed(
                url,
                error=result.error or "fetch failed",
                http_status=result.status_code,
            )
            raise RuntimeError(result.error or f"Failed to fetch {url}")
        event_logger.website_fetch_success(url, http_status=result.status_code or 0)
        return result.html

    return fetch


def enrich_customer_website(
    candidate: EnrichmentCandidate,
    *,
    requested_fields: list[str] | None = None,
    max_pages: int = 10,
    fetcher: Callable[[str], str] | None = None,
    run_id: UUID | None = None,
    run_logger: ScraperRunLogger | None = None,
) -> EnrichmentResultDto:
    requested = {
        field
        for field in (requested_fields or ["email"])
        if field in ENRICHMENT_REQUESTED_FIELD_KEYS
    }
    if not requested:
        requested = {"email"}

    event_logger: EnrichmentCustomerRunLogger | None = None
    if run_logger is not None and run_id is not None:
        event_logger = EnrichmentCustomerRunLogger(run_logger, run_id=run_id, candidate=candidate)
        event_logger.candidate_selected()

    active_fetcher = fetcher
    if active_fetcher is None and event_logger is not None:
        active_fetcher = _build_logging_fetcher(event_logger)

    social_links_empty = {key: None for key in ("instagram", "facebook", "linkedin", "youtube")}

    try:
        pages = crawl_customer_website(
            candidate.website,
            max_pages=max_pages,
            fetcher=active_fetcher,
        )
    except Exception as exc:
        result = EnrichmentResultDto(
            customer_id=candidate.customer_id,
            company_name=candidate.company_name,
            website=candidate.website,
            status="failed",
            error=str(exc),
            social_links=social_links_empty,
        )
        if event_logger is not None:
            event_logger.log_result(result)
        return result

    if not pages:
        result = EnrichmentResultDto(
            customer_id=candidate.customer_id,
            company_name=candidate.company_name,
            website=candidate.website,
            status="failed",
            error="Website could not be fetched",
            social_links=social_links_empty,
        )
        if event_logger is not None:
            event_logger.log_result(result)
        return result

    emails: list[SourcedValue] = []
    phones: list[SourcedValue] = []
    address: SourcedValue | None = None
    social_links: dict[str, SourcedValue | None] = dict(social_links_empty)

    for page_url, html in pages:
        extracted = extract_contacts_from_html(
            html,
            source_url=page_url,
            requested_fields=requested,
        )
        emails = _merge_sourced_values(emails, extracted.get("emails", []))  # type: ignore[arg-type]
        phones = _merge_sourced_values(phones, extracted.get("phones", []))  # type: ignore[arg-type]
        if address is None and extracted.get("address") is not None:
            address = extracted["address"]  # type: ignore[assignment]
        page_social = extracted.get("social_links") or {}
        if isinstance(page_social, dict):
            for key, value in page_social.items():
                if value is not None and social_links.get(key) is None:
                    social_links[key] = value

    result = EnrichmentResultDto(
        customer_id=candidate.customer_id,
        company_name=candidate.company_name,
        website=candidate.website,
        emails=emails,
        phones=phones,
        address=address,
        social_links=social_links,
        status="not_found",
    )
    if _has_requested_data(result, requested):
        result = EnrichmentResultDto(
            customer_id=result.customer_id,
            company_name=result.company_name,
            website=result.website,
            emails=result.emails,
            phones=result.phones,
            address=result.address,
            social_links=result.social_links,
            status="found",
        )

    if event_logger is not None:
        event_logger.log_result(result)
    return result


def enrich_customer_by_id(
    *,
    customer_id: UUID,
    company_name: str,
    website: str,
    requested_fields: list[str] | None = None,
    max_pages: int = 10,
    fetcher: Callable[[str], str] | None = None,
    run_id: UUID | None = None,
    run_logger: ScraperRunLogger | None = None,
) -> EnrichmentResultDto:
    candidate = EnrichmentCandidate(
        customer_id=customer_id,
        company_name=company_name,
        website=website,
    )
    return enrich_customer_website(
        candidate,
        requested_fields=requested_fields,
        max_pages=max_pages,
        fetcher=fetcher,
        run_id=run_id,
        run_logger=run_logger,
    )

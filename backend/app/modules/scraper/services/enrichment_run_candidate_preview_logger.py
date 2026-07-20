"""Standard pre-scan candidate preview logs for bulk enrichment runs."""

from __future__ import annotations

from app.modules.scraper.core.scraper_run_logger import ScraperRunLogger
from app.modules.scraper.services.enrichment_candidate_service import EnrichmentCandidate


def enrichment_candidate_display_name(candidate: EnrichmentCandidate) -> str:
    """Return a user-facing company label, reusing the same safe fallbacks as run logs."""
    name = (candidate.company_name or "").strip()
    if name:
        return name
    website = (candidate.website or "").strip()
    if website:
        return website
    return f"Müşteri {str(candidate.customer_id)[:8]}"


def log_bulk_enrichment_candidate_preview(
    run_logger: ScraperRunLogger,
    candidates: list[EnrichmentCandidate],
) -> None:
    """Log the post-limit candidate batch before any website scan starts.

    Intended for org-wide and fair-scoped bulk runs started from EnrichmentRunPanel.
    Uses the already-selected candidate list — no second query.
    """
    count = len(candidates)
    run_logger.info(
        "candidates_to_process",
        f"{count} firma işleme alınacak.",
        metadata={"candidate_count": count},
    )
    if count == 0:
        return

    run_logger.info("candidates_list_header", "İşleme alınacak firmalar:")
    for index, candidate in enumerate(candidates, start=1):
        display_name = enrichment_candidate_display_name(candidate)
        run_logger.info(
            "candidate_preview",
            f"{index}. {display_name}",
            metadata={
                "index": index,
                "customer_id": str(candidate.customer_id),
                "company_name": display_name,
                "website": candidate.website,
            },
        )

    run_logger.info("scan_batch_started", "Tarama başlatılıyor...")


def log_customer_scan_started(
    run_logger: ScraperRunLogger,
    candidate: EnrichmentCandidate,
) -> None:
    display_name = enrichment_candidate_display_name(candidate)
    run_logger.info(
        "customer_scan_started",
        f"{display_name} taranıyor...",
        metadata={
            "customer_id": str(candidate.customer_id),
            "company_name": display_name,
            "website": candidate.website,
        },
    )


def log_customer_scan_finished(
    run_logger: ScraperRunLogger,
    candidate: EnrichmentCandidate,
) -> None:
    display_name = enrichment_candidate_display_name(candidate)
    run_logger.info(
        "customer_scan_finished",
        f"{display_name} tamamlandı.",
        metadata={
            "customer_id": str(candidate.customer_id),
            "company_name": display_name,
            "website": candidate.website,
        },
    )

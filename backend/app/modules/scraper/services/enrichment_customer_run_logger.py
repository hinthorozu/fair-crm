"""Structured per-customer run log events for contact enrichment."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.scraper.core.scraper_run_logger import ScraperRunLogger
from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto
from app.modules.scraper.services.enrichment_candidate_service import EnrichmentCandidate


class EnrichmentCustomerRunLogger:
    def __init__(
        self,
        run_logger: ScraperRunLogger,
        *,
        run_id: UUID,
        candidate: EnrichmentCandidate,
    ) -> None:
        self._run_logger = run_logger
        self._run_id = run_id
        self._candidate = candidate

    def _base_metadata(self, **extra: Any) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "run_id": str(self._run_id),
            "customer_id": str(self._candidate.customer_id),
            "company_name": self._candidate.company_name,
            "website": self._candidate.website,
        }
        metadata.update(extra)
        return metadata

    def candidate_selected(self) -> None:
        self._run_logger.info(
            "candidate_selected",
            f"Aday seçildi: {self._candidate.company_name}",
            metadata=self._base_metadata(status="selected"),
        )

    def website_fetch_started(self, fetched_url: str) -> None:
        self._run_logger.info(
            "website_fetch_started",
            f"Sayfa isteniyor: {fetched_url}",
            metadata=self._base_metadata(fetched_url=fetched_url, status="fetching"),
        )

    def website_fetch_success(self, fetched_url: str, *, http_status: int) -> None:
        self._run_logger.info(
            "website_fetch_success",
            f"Sayfa alındı: {fetched_url}",
            metadata=self._base_metadata(
                fetched_url=fetched_url,
                http_status=http_status,
                status="fetch_ok",
            ),
        )

    def website_fetch_failed(
        self,
        fetched_url: str,
        *,
        error: str,
        http_status: int | None = None,
    ) -> None:
        metadata = self._base_metadata(
            fetched_url=fetched_url,
            error=error,
            status="fetch_failed",
        )
        if http_status is not None:
            metadata["http_status"] = http_status
        self._run_logger.warning(
            "website_fetch_failed",
            f"Sayfa alınamadı: {fetched_url}",
            metadata=metadata,
        )

    def contact_extracted(self, result: EnrichmentResultDto) -> None:
        found_emails = [item.value for item in result.emails]
        metadata = self._base_metadata(
            status=result.status,
            found_emails_count=len(found_emails),
            found_email_values=found_emails,
            source_url=(
                result.emails[0].source_url
                if result.emails
                else result.phones[0].source_url
                if result.phones
                else result.website
            ),
        )
        if result.error:
            metadata["error"] = result.error
        self._run_logger.info(
            "contact_extracted",
            f"İletişim çıkarımı tamamlandı: {self._candidate.company_name}",
            metadata=metadata,
        )

    def email_found(self, result: EnrichmentResultDto) -> None:
        found_emails = [item.value for item in result.emails]
        self._run_logger.info(
            "email_found",
            f"E-posta bulundu: {self._candidate.company_name}",
            metadata=self._base_metadata(
                status="found",
                found_emails_count=len(found_emails),
                found_email_values=found_emails,
                source_url=result.emails[0].source_url if result.emails else None,
            ),
        )

    def not_found(self, result: EnrichmentResultDto) -> None:
        self._run_logger.info(
            "not_found",
            f"İletişim bulunamadı: {self._candidate.company_name}",
            metadata=self._base_metadata(
                status="not_found",
                found_emails_count=0,
                found_email_values=[],
                source_url=result.website,
            ),
        )

    def log_result(self, result: EnrichmentResultDto) -> None:
        self.contact_extracted(result)
        if result.status == "failed":
            return
        if result.emails:
            self.email_found(result)
        elif result.status == "not_found":
            self.not_found(result)

    def handoff_row_created(self, *, source_url: str | None) -> None:
        self._run_logger.info(
            "handoff_row_created",
            f"Handoff satırı oluşturuldu: {self._candidate.company_name}",
            metadata=self._base_metadata(
                status="found",
                source_url=source_url or self._candidate.website,
            ),
        )

    def handoff_row_skipped(self, *, reason: str) -> None:
        self._run_logger.info(
            "handoff_row_skipped",
            f"Handoff satırı atlandı: {self._candidate.company_name}",
            metadata=self._base_metadata(status=reason, source_url=self._candidate.website),
        )

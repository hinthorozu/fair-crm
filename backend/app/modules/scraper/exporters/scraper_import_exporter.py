"""Prepare scraper output for Import Engine preview handoff."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.modules.scraper.types.scraper_result import ScraperResult


@dataclass(frozen=True)
class ScraperImportHandoff:
    """Payload for Import Preview — no CRM writes or merge decisions."""

    canonical_rows: list[dict[str, str]]
    metadata: dict[str, Any] = field(default_factory=dict)
    row_metadata: list[dict[str, Any]] = field(default_factory=list)


class ScraperImportExporter:
    """Maps ``ScraperResult`` normalized companies to import canonical rows."""

    def export(
        self,
        result: ScraperResult,
        *,
        fair_name: str | None = None,
        fair_year: int | str | None = None,
        source_url: str | None = None,
    ) -> ScraperImportHandoff:
        canonical_rows = [company.to_canonical_row() for company in result.companies]
        adapter_name = result.metadata.get("adapter") or result.site_key

        metadata: dict[str, Any] = {
            "fair_name": fair_name if fair_name is not None else result.metadata.get("fair_name"),
            "fair_year": fair_year if fair_year is not None else result.metadata.get("fair_year"),
            "source_site": result.site_key,
            "source_url": (
                source_url
                if source_url is not None
                else result.metadata.get("source_url") or result.metadata.get("list_url")
            ),
            "adapter_name": adapter_name,
            "raw_count": result.raw_count,
            "normalized_count": result.normalized_count,
            "warnings": list(result.warnings),
            "errors": list(result.errors),
        }
        if result.scraped_at is not None:
            metadata["scraped_at"] = result.scraped_at.isoformat()
        if result.fair_id is not None:
            metadata["fair_id"] = str(result.fair_id)

        for key, value in result.metadata.items():
            metadata.setdefault(key, value)

        row_metadata: list[dict[str, Any]] = []
        for company in result.companies:
            company_meta = dict(company.metadata or {})
            row_metadata.append(
                {
                    "source_url": company.source_url,
                    "adapter_name": adapter_name,
                    **company_meta,
                }
            )

        return ScraperImportHandoff(
            canonical_rows=canonical_rows,
            metadata=metadata,
            row_metadata=row_metadata,
        )

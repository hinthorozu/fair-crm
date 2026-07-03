"""Aggregate scrape output."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.scraper.dto.normalized_company_dto import NormalizedCompanyDto


@dataclass(frozen=True)
class ScraperResult:
    site_key: str
    fair_id: UUID | None
    companies: list[NormalizedCompanyDto]
    raw_count: int
    normalized_count: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    scraped_at: datetime | None = None

    def to_canonical_rows(self) -> list[dict[str, str]]:
        return [company.to_canonical_row() for company in self.companies]

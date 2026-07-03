"""Scraper execution context passed to site adapters."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ScraperContext:
    """Input for a single scrape run."""

    fair_id: UUID | None = None
    list_url: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

"""In-memory scraper job model (persistence layer comes later)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.modules.scraper.types.scraper_context import ScraperContext
from app.modules.scraper.types.scraper_result import ScraperResult


class ScraperJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class ScraperJob:
    id: UUID
    site_key: str
    status: ScraperJobStatus
    context: ScraperContext
    result: ScraperResult | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

"""Domain types for adapter scraper run history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.modules.scraper.domain.scraper_run_source import ScraperRunSource


class ScraperRunStatus(StrEnum):
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_SCRAPER_RUN_STATUSES = frozenset(
    {
        ScraperRunStatus.RUNNING,
        ScraperRunStatus.CANCEL_REQUESTED,
        ScraperRunStatus.CANCELLING,
    }
)


@dataclass(frozen=True)
class ScraperRunHistory:
    id: UUID
    adapter_key: str
    status: ScraperRunStatus
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    organization_id: UUID | None
    fair_id: UUID | None
    input_url: str | None
    fair_name: str | None
    fair_year: int | None
    total_rows: int
    website_count: int
    email_count: int
    phone_count: int
    instagram_count: int
    linkedin_count: int
    facebook_count: int
    youtube_count: int
    x_count: int
    error_message: str | None
    output_json_path: str | None
    output_excel_path: str | None
    run_source: ScraperRunSource = ScraperRunSource.MANUAL_TEST
    import_batch_id: UUID | None = None
    cancel_requested_by: UUID | None = None
    cancel_requested_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    progress_current: int | None = None
    progress_total: int | None = None

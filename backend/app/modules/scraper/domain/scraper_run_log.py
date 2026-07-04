"""Domain types for adapter scraper run console logs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class ScraperRunLogLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass(frozen=True)
class ScraperRunLog:
    id: UUID
    run_id: UUID
    level: ScraperRunLogLevel
    step: str
    message: str
    created_at: datetime
    metadata: dict[str, Any] | None = None

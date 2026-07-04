"""Domain types for fairs linked to a scraper adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AdapterLinkedFair:
    id: UUID | None
    name: str
    venue: str | None
    city: str | None
    status: str | None
    source_url: str | None
    last_import_at: datetime | None

"""Result model for customer website contact enrichment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

EnrichmentStatus = Literal["found", "not_found", "skipped", "failed"]


@dataclass(frozen=True)
class SourcedValue:
    value: str
    source_url: str


@dataclass(frozen=True)
class EnrichmentResultDto:
    customer_id: UUID
    company_name: str
    website: str
    emails: list[SourcedValue] = field(default_factory=list)
    phones: list[SourcedValue] = field(default_factory=list)
    address: SourcedValue | None = None
    social_links: dict[str, SourcedValue | None] = field(default_factory=dict)
    status: EnrichmentStatus = "not_found"
    error: str | None = None

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "customer_id": str(self.customer_id),
            "company_name": self.company_name,
            "website": self.website,
            "emails": [{"value": item.value, "source_url": item.source_url} for item in self.emails],
            "phones": [{"value": item.value, "source_url": item.source_url} for item in self.phones],
            "address": (
                {"value": self.address.value, "source_url": self.address.source_url}
                if self.address is not None
                else None
            ),
            "social_links": {
                key: (
                    {"value": item.value, "source_url": item.source_url}
                    if item is not None
                    else None
                )
                for key, item in self.social_links.items()
            },
            "status": self.status,
            "error": self.error,
        }

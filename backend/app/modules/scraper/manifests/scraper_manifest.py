"""Declarative scraper adapter manifest model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


from app.modules.scraper.domain.adapter_engine import AdapterEngineType


class ScraperStatus(StrEnum):
    STABLE = "stable"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


@dataclass(frozen=True)
class ScraperSupports:
    list_scraping: bool = False
    detail_scraping: bool = False
    pagination: bool = False
    website: bool = False
    email: bool = False
    phone: bool = False
    address: bool = False
    category: bool = False
    description: bool = False


@dataclass(frozen=True)
class ScraperOutput:
    json_handoff: bool = False
    excel: bool = False


@dataclass(frozen=True)
class ScraperBrowser:
    requires_js: bool = False
    requires_playwright: bool = False


@dataclass(frozen=True)
class ScraperManifest:
    """Declarative capability and status declaration for a scraper adapter."""

    adapter_key: str
    display_name: str
    version: str
    supported_sites: tuple[str, ...]
    supports: ScraperSupports
    output: ScraperOutput
    browser: ScraperBrowser
    status: ScraperStatus
    author: str
    notes: str
    scraper_version: str = "1.0"
    target_site_version: str = "unknown"
    last_verified: str | None = None
    engine_type: AdapterEngineType = AdapterEngineType.STATIC

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["engine_type"] = self.engine_type.value
        return payload

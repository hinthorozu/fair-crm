"""Canonical import document schema — source-agnostic contract for Import Engine."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CanonicalImportSourceType(StrEnum):
    SCRAPER = "scraper"
    EXCEL = "excel"
    CSV = "csv"
    API = "api"


class CanonicalImportSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: CanonicalImportSourceType
    adapter_key: str | None = None
    fair_id: UUID | None = None
    run_id: UUID | None = None
    source_url: str | None = None

    @model_validator(mode="after")
    def validate_scraper_source(self) -> CanonicalImportSource:
        if self.type == CanonicalImportSourceType.SCRAPER and not (self.adapter_key or "").strip():
            raise ValueError("adapter_key is required when source.type is scraper")
        return self


class CanonicalImportMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    created_at: datetime
    row_count: int = Field(ge=0)


class CanonicalImportRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_id: str | None = None
    company_name: str = Field(min_length=1)
    normalized_company_name: str = Field(min_length=1)
    website: str | None = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    country: str | None = None
    city: str | None = None
    hall: str | None = None
    stand: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None
    linkedin_url: str | None = None
    youtube_url: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class CanonicalImportDocument(BaseModel):
    """Vendor-neutral import payload consumed by Import Engine."""

    model_config = ConfigDict(extra="forbid")

    source: CanonicalImportSource
    metadata: CanonicalImportMetadata
    rows: list[CanonicalImportRow]

    @model_validator(mode="after")
    def validate_row_count(self) -> CanonicalImportDocument:
        if self.metadata.row_count != len(self.rows):
            raise ValueError("metadata.row_count must match len(rows)")
        return self

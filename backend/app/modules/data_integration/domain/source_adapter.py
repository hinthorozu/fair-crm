"""Universal Source Adapter protocol (Sprint 09.2).

Every data source (Excel, CSV, scraper, ERP, …) implements the same lifecycle.
Adapters read and normalize source data only — they never write to CRM tables.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.modules.imports.domain.value_objects import ImportSourceType


@dataclass(frozen=True)
class SourceConnection:
    """Adapter input — file bytes, API credentials, scraper URL, etc."""

    payload: bytes
    file_name: str | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class RawSourceData:
    """Tabular raw output from Read Source — no CRM field semantics."""

    columns: list[str]
    rows: list[list[Any]]
    total_rows: int
    detected_headers: list[str]
    sheet_name: str | None = None
    available_sheets: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SourceAdapter(Protocol):
    """Universal adapter lifecycle: Connect → Read → Normalize → Preview."""

    @property
    def source_type(self) -> ImportSourceType:
        """Registered source type for this adapter."""

    def connect(self, connection: SourceConnection) -> None:
        """Validate source payload and connection options."""

    def read_source(
        self,
        connection: SourceConnection,
        *,
        sheet_name: str | None = None,
    ) -> RawSourceData:
        """Extract raw tabular data from the source."""

    def normalize(self, raw: RawSourceData) -> dict[str, Any]:
        """Convert raw data to the import engine preview contract."""

    def preview(
        self,
        connection: SourceConnection,
        *,
        sheet_name: str | None = None,
    ) -> dict[str, Any]:
        """Full adapter pipeline: connect → read → normalize → preview dict."""

"""Legacy import adapter protocol — superseded by domain.source_adapter.SourceAdapter."""

from typing import Any, Protocol

from app.modules.data_integration.domain.source_adapter import SourceAdapter


class ImportAdapter(Protocol):
    """Deprecated alias — use SourceAdapter from domain.source_adapter."""

    def analyze(self, file_content: bytes, *, sheet_name: str | None = None) -> dict[str, Any]:
        """Return raw preview matrix + metadata without CRM semantics."""


def preview_from_bytes(
    adapter: SourceAdapter,
    file_content: bytes,
    *,
    file_name: str | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Helper for legacy call sites migrating to SourceAdapter."""
    from app.modules.data_integration.domain.source_adapter import SourceConnection

    return adapter.preview(
        SourceConnection(payload=file_content, file_name=file_name),
        sheet_name=sheet_name,
    )

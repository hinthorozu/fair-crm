"""Resolve adapter instance keys to underlying engine keys for scraping."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from dataclasses import dataclass

from app.modules.scraper.core.manifest_registry import ManifestRegistry, get_manifest_registry
from app.modules.scraper.domain.scraper_adapter import normalize_adapter_key
from app.modules.scraper.domain.scraper_adapter_exceptions import AdapterEngineNotFoundError
from app.modules.scraper.domain.requested_output_fields import requested_fields_from_overlay
from app.modules.scraper.infrastructure.repositories.scraper_adapter_repository import ScraperAdapterRepository


@dataclass(frozen=True)
class AdapterOutputFormats:
    json_handoff: bool
    excel: bool


def resolve_output_formats(
    session: Session,
    organization_id: UUID,
    instance_key: str,
    *,
    manifest_registry: ManifestRegistry | None = None,
    output_json_override: bool | None = None,
    output_excel_override: bool | None = None,
) -> AdapterOutputFormats:
    """Resolve JSON/Excel export flags from manifest defaults plus instance overlay."""
    normalized_instance = normalize_adapter_key(instance_key)
    registry = manifest_registry or get_manifest_registry()
    try:
        base_manifest = registry.get(normalized_instance)
    except KeyError:
        base_manifest = None

    json_handoff = bool(base_manifest.output.json_handoff) if base_manifest is not None else True
    excel = bool(base_manifest.output.excel) if base_manifest is not None else False

    repository = ScraperAdapterRepository(session)
    record = repository.get_by_key(organization_id, normalized_instance)
    if record is not None:
        overlay_output = (record.manifest or {}).get("output") or {}
        if overlay_output.get("json_handoff") is not None:
            json_handoff = bool(overlay_output["json_handoff"])
        if overlay_output.get("excel") is not None:
            excel = bool(overlay_output["excel"])

    if output_json_override is not None:
        json_handoff = output_json_override
    if output_excel_override is not None:
        excel = output_excel_override

    return AdapterOutputFormats(json_handoff=json_handoff, excel=excel)


def resolve_requested_fields(
    session: Session,
    organization_id: UUID,
    instance_key: str,
) -> list[str]:
    """Load user-selected output fields from adapter instance overlay (or defaults)."""
    normalized_instance = normalize_adapter_key(instance_key)
    repository = ScraperAdapterRepository(session)
    record = repository.get_by_key(organization_id, normalized_instance)
    if record is None:
        return requested_fields_from_overlay(None)
    return requested_fields_from_overlay(record.manifest)


def resolve_engine_key(
    session: Session,
    organization_id: UUID,
    instance_key: str,
    *,
    manifest_registry: ManifestRegistry | None = None,
) -> str:
    """Map an adapter instance key to the engine key used by the code registry."""
    normalized_instance = normalize_adapter_key(instance_key)
    repository = ScraperAdapterRepository(session)
    record = repository.get_by_key(organization_id, normalized_instance)
    if record is not None:
        return record.engine_key

    registry = manifest_registry or get_manifest_registry()
    try:
        registry.get(normalized_instance)
    except KeyError as exc:
        raise AdapterEngineNotFoundError(f"Adapter engine not found for instance: {instance_key}") from exc
    return normalized_instance

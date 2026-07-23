"""User-selected scraper output fields (requested fields) shared by static and dynamic engines."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from app.modules.scraper.types.scraper_context import ScraperContext

if TYPE_CHECKING:
    from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff

REQUESTED_OUTPUT_FIELD_KEYS: tuple[str, ...] = (
    "customerName",
    "phone",
    "email",
    "address",
    "website",
    "hall",
    "stand",
    "instagram",
    "facebook",
    "linkedin",
    "youtube",
    "notes",
)

DEFAULT_REQUESTED_FIELDS: tuple[str, ...] = REQUESTED_OUTPUT_FIELD_KEYS

# Legacy alias; all standard fields are default-on per scraper output field contract.
OPTIONAL_DEFAULT_OFF_FIELDS: frozenset[str] = frozenset()

# Maps requested output key -> canonical handoff row key.
from app.shared.import_output_fields import OUTPUT_KEY_TO_CANONICAL

FIELD_TO_CANONICAL: dict[str, str] = OUTPUT_KEY_TO_CANONICAL

# Maps requested output key -> row_metadata key for social URLs.
FIELD_TO_METADATA: dict[str, str] = {
    "instagram": "instagram_url",
    "facebook": "facebook_url",
    "linkedin": "linkedin_url",
    "youtube": "youtube_url",
}

LIST_PAGE_FIELDS: frozenset[str] = frozenset({"customerName", "hall", "stand"})

DETAIL_PAGE_FIELDS: frozenset[str] = frozenset(
    {"phone", "email", "address", "website", "instagram", "facebook", "linkedin", "youtube", "notes"}
)

_VALID_FIELDS: frozenset[str] = frozenset(REQUESTED_OUTPUT_FIELD_KEYS)

# Always kept in handoff rows even when not user-requested (matching / identity).
_HANDOFF_PRESERVE_CANONICAL_KEYS: frozenset[str] = frozenset({"company_name"})

# Always kept in row metadata (enrichment customer_id matching, traceability).
_HANDOFF_PRESERVE_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "external_id",
        "customer_id",
        "enrichment_status",
        "source_url",
        "email_source_url",
        "phone_source_url",
        "address_source_url",
    }
)


def output_field_capabilities_from_supports(supports: Any) -> dict[str, bool]:
    """Map legacy manifest ``ScraperSupports`` flags to standard output field keys."""
    return {
        "customerName": bool(getattr(supports, "list_scraping", False)),
        "phone": bool(getattr(supports, "phone", False)),
        "email": bool(getattr(supports, "email", False)),
        "address": bool(getattr(supports, "address", False)),
        "website": bool(getattr(supports, "website", False)),
        "hall": bool(getattr(supports, "list_scraping", False)),
        "stand": bool(getattr(supports, "list_scraping", False)),
        "instagram": bool(getattr(supports, "detail_scraping", False)),
        "facebook": bool(getattr(supports, "detail_scraping", False)),
        "linkedin": bool(getattr(supports, "detail_scraping", False)),
        "youtube": bool(getattr(supports, "detail_scraping", False)),
        "notes": bool(getattr(supports, "description", False)),
    }


def default_requested_fields_for_capabilities(
    capabilities: dict[str, bool] | None,
) -> list[str]:
    if capabilities is None:
        return list(DEFAULT_REQUESTED_FIELDS)
    if _is_enrichment_capabilities(capabilities):
        from app.modules.scraper.domain.enrichment_adapter import DEFAULT_ENRICHMENT_REQUESTED_FIELDS

        return [
            field
            for field in DEFAULT_ENRICHMENT_REQUESTED_FIELDS
            if capabilities.get(field)
        ] or [
            field
            for field in ("email", "phone", "address", "instagram", "facebook", "linkedin", "youtube")
            if capabilities.get(field)
        ]
    return [field for field in REQUESTED_OUTPUT_FIELD_KEYS if capabilities.get(field)]


def _is_enrichment_capabilities(capabilities: dict[str, bool]) -> bool:
    return (
        capabilities.get("email")
        and not capabilities.get("customerName")
        and not capabilities.get("website")
        and not capabilities.get("hall")
    )


def filter_requested_fields_by_capabilities(
    fields: list[str],
    capabilities: dict[str, bool] | None,
) -> list[str]:
    if capabilities is None:
        return [field for field in REQUESTED_OUTPUT_FIELD_KEYS if field in fields]
    return [
        field
        for field in REQUESTED_OUTPUT_FIELD_KEYS
        if field in fields and capabilities.get(field)
    ]


def resolve_requested_fields_for_manifest(
    overlay: dict[str, Any] | None,
    supports: Any,
) -> list[str]:
    """Resolve stored or default requested fields, filtered by engine capabilities."""
    capabilities = output_field_capabilities_from_supports(supports)
    if not overlay:
        return default_requested_fields_for_capabilities(capabilities)

    raw = overlay.get("requested_fields")
    if raw is None:
        return default_requested_fields_for_capabilities(capabilities)
    if not isinstance(raw, (list, tuple)):
        return default_requested_fields_for_capabilities(capabilities)

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw:
        key = str(item).strip()
        if not key or key not in _VALID_FIELDS or key in seen:
            continue
        seen.add(key)
        normalized.append(key)

    if not normalized:
        return default_requested_fields_for_capabilities(capabilities)

    filtered = filter_requested_fields_by_capabilities(normalized, capabilities)
    return filtered or default_requested_fields_for_capabilities(capabilities)


def normalize_requested_fields(
    value: list[str] | tuple[str, ...] | None,
    *,
    capabilities: dict[str, bool] | None = None,
) -> list[str]:
    """Return a de-duplicated ordered list of valid requested field keys."""
    if not value:
        return default_requested_fields_for_capabilities(capabilities)

    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        key = str(item).strip()
        if not key or key not in _VALID_FIELDS or key in seen:
            continue
        seen.add(key)
        normalized.append(key)

    if not normalized:
        return default_requested_fields_for_capabilities(capabilities)

    filtered = filter_requested_fields_by_capabilities(normalized, capabilities)
    return filtered or default_requested_fields_for_capabilities(capabilities)


def requested_fields_from_overlay(overlay: dict[str, Any] | None) -> list[str]:
    if not overlay:
        return list(DEFAULT_REQUESTED_FIELDS)
    raw = overlay.get("requested_fields")
    if raw is None:
        return list(DEFAULT_REQUESTED_FIELDS)
    if isinstance(raw, (list, tuple)):
        return normalize_requested_fields(list(raw))
    return list(DEFAULT_REQUESTED_FIELDS)


def resolve_requested_fields_from_context(context: ScraperContext) -> list[str]:
    raw = context.options.get("requested_fields")
    if raw is None:
        return list(DEFAULT_REQUESTED_FIELDS)
    if isinstance(raw, (list, tuple)):
        return normalize_requested_fields(list(raw))
    return list(DEFAULT_REQUESTED_FIELDS)


def needs_detail_scrape(requested_fields: list[str]) -> bool:
    requested = set(normalize_requested_fields(requested_fields))
    return bool(requested & DETAIL_PAGE_FIELDS)


def filter_handoff_by_requested_fields(
    handoff: ScraperImportHandoff,
    requested_fields: list[str] | None,
) -> ScraperImportHandoff:
    """Keep only user-requested fields in canonical rows and row metadata."""
    requested = normalize_requested_fields(requested_fields)
    requested_set = set(requested)

    canonical_keys = {
        FIELD_TO_CANONICAL[field]
        for field in requested_set
        if field in FIELD_TO_CANONICAL
    }
    metadata_keys = {
        FIELD_TO_METADATA[field]
        for field in requested_set
        if field in FIELD_TO_METADATA
    }

    row_metadata = handoff.row_metadata or []
    filtered_rows: list[dict[str, str]] = []
    filtered_metadata: list[dict[str, Any]] = []

    for index, row in enumerate(handoff.canonical_rows or []):
        filtered_rows.append(
            {
                key: value
                for key, value in row.items()
                if key in canonical_keys or key in _HANDOFF_PRESERVE_CANONICAL_KEYS
            }
        )

        source_meta = row_metadata[index] if index < len(row_metadata) else {}
        filtered_meta: dict[str, Any] = {}
        for meta_key in _HANDOFF_PRESERVE_METADATA_KEYS:
            value = source_meta.get(meta_key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                filtered_meta[meta_key] = text
        for meta_key, value in source_meta.items():
            if not meta_key.endswith("_source_url") or meta_key in filtered_meta:
                continue
            text = str(value).strip()
            if text:
                filtered_meta[meta_key] = text
        for meta_key in metadata_keys:
            value = source_meta.get(meta_key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                filtered_meta[meta_key] = text
        filtered_metadata.append(filtered_meta)

    return replace(
        handoff,
        canonical_rows=filtered_rows,
        row_metadata=filtered_metadata,
    )

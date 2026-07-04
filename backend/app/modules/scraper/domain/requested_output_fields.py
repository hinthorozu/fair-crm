"""User-selected scraper output fields (requested fields) shared by static and dynamic engines."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.types.scraper_context import ScraperContext

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

DEFAULT_REQUESTED_FIELDS: tuple[str, ...] = (
    "customerName",
    "phone",
    "email",
    "address",
    "website",
    "hall",
    "stand",
)

OPTIONAL_DEFAULT_OFF_FIELDS: frozenset[str] = frozenset(
    {"instagram", "facebook", "linkedin", "youtube", "notes"}
)

# Maps requested output key -> canonical handoff row key.
FIELD_TO_CANONICAL: dict[str, str] = {
    "customerName": "company_name",
    "phone": "phone",
    "email": "email",
    "address": "address",
    "website": "website",
    "hall": "hall",
    "stand": "stand",
    "notes": "notes",
    "instagram": "instagram_url",
    "facebook": "facebook_url",
    "linkedin": "linkedin_url",
    "youtube": "youtube_url",
}

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


def normalize_requested_fields(value: list[str] | tuple[str, ...] | None) -> list[str]:
    """Return a de-duplicated ordered list of valid requested field keys."""
    if not value:
        return list(DEFAULT_REQUESTED_FIELDS)

    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        key = str(item).strip()
        if not key or key not in _VALID_FIELDS or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized or list(DEFAULT_REQUESTED_FIELDS)


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
        filtered_rows.append({key: value for key, value in row.items() if key in canonical_keys})

        source_meta = row_metadata[index] if index < len(row_metadata) else {}
        filtered_meta: dict[str, Any] = {}
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

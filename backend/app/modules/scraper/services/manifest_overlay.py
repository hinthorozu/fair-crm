"""Merge registry manifests with organization-specific adapter overlays."""

from __future__ import annotations

import re
from dataclasses import asdict, replace
from datetime import UTC, date, datetime
from typing import Any

from app.modules.scraper.domain.scraper_adapter import ScraperAdapter
from app.modules.scraper.manifests.scraper_manifest import (
    ScraperBrowser,
    ScraperManifest,
    ScraperOutput,
    ScraperStatus,
    ScraperSupports,
)

_SITE_SPLIT_PATTERN = re.compile(r"[,\n]+")


def normalize_supported_sites(value: list[str] | str | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = _SITE_SPLIT_PATTERN.split(value)
    else:
        parts = value
    normalized: list[str] = []
    seen: set[str] = set()
    for part in parts:
        cleaned = str(part).strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def parse_last_verified(value: str | None) -> datetime | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    parsed = date.fromisoformat(cleaned)
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=UTC)


def format_last_verified(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).date().isoformat()


def _merge_mapping(base: dict[str, Any], patch: dict[str, Any] | None) -> dict[str, Any]:
    if not patch:
        return dict(base)
    merged = dict(base)
    for key, item in patch.items():
        if item is not None:
            merged[key] = item
    return merged


def merge_manifest_with_record(base: ScraperManifest, record: ScraperAdapter | None) -> ScraperManifest:
    if record is None:
        return base

    overlay = record.manifest or {}
    supported_sites_raw = overlay.get("supported_sites", base.supported_sites)
    if isinstance(supported_sites_raw, str):
        supported_sites = tuple(normalize_supported_sites(supported_sites_raw))
    elif isinstance(supported_sites_raw, (list, tuple)):
        supported_sites = tuple(normalize_supported_sites(list(supported_sites_raw)))
    else:
        supported_sites = base.supported_sites

    supports = replace(
        base.supports,
        **_merge_mapping(asdict(base.supports), overlay.get("supports")),
    )
    output = replace(
        base.output,
        **_merge_mapping(asdict(base.output), overlay.get("output")),
    )
    browser = replace(
        base.browser,
        **_merge_mapping(asdict(base.browser), overlay.get("browser")),
    )

    last_verified = format_last_verified(record.last_verified_at) or base.last_verified

    return ScraperManifest(
        adapter_key=base.adapter_key,
        display_name=record.name,
        version=record.version or base.version,
        supported_sites=supported_sites,
        supports=supports,
        output=output,
        browser=browser,
        status=record.status,
        author=base.author,
        notes=record.description if record.description is not None else ("" if record is not None else base.notes),
        scraper_version=base.scraper_version,
        target_site_version=base.target_site_version,
        last_verified=last_verified,
    )


def build_manifest_overlay_patch(
    existing: dict[str, Any] | None,
    *,
    supported_sites: list[str] | str | None = None,
    output: dict[str, bool] | None = None,
    browser: dict[str, bool] | None = None,
    supports: dict[str, bool] | None = None,
    requested_fields: list[str] | None = None,
) -> dict[str, Any]:
    overlay = dict(existing or {})
    if supported_sites is not None:
        overlay["supported_sites"] = normalize_supported_sites(supported_sites)
    if output is not None:
        overlay["output"] = _merge_mapping(overlay.get("output") or {}, output)
    if browser is not None:
        overlay["browser"] = _merge_mapping(overlay.get("browser") or {}, browser)
    if supports is not None:
        overlay["supports"] = _merge_mapping(overlay.get("supports") or {}, supports)
    if requested_fields is not None:
        overlay["requested_fields"] = list(requested_fields)
    return overlay


def validate_manifest_status(value: str) -> ScraperStatus:
    try:
        return ScraperStatus(value)
    except ValueError as exc:
        raise ValueError(f"status must be one of: {', '.join(s.value for s in ScraperStatus)}") from exc

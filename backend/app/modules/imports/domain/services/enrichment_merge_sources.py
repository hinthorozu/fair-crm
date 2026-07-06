"""Extract enrichment source URLs from import row metadata for merge preview."""

from __future__ import annotations

from typing import Any

# Merge preview field_key -> metadata key inside canonical row.raw
ENRICHMENT_FIELD_SOURCE_KEYS: dict[str, str] = {
    "email": "email_source_url",
    "phone": "phone_source_url",
    "address": "address_source_url",
    "website": "source_url",
    "instagram_url": "instagram_source_url",
    "facebook_url": "facebook_source_url",
    "linkedin_url": "linkedin_source_url",
    "youtube_url": "youtube_source_url",
}


def _clean_url(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text.startswith(("http://", "https://")):
        return None
    return text


def _raw_metadata_blob(raw_data_json: dict[str, Any] | None) -> dict[str, Any]:
    if not raw_data_json:
        return {}
    nested = raw_data_json.get("raw")
    if isinstance(nested, dict):
        return nested
    return raw_data_json


def extract_enrichment_field_sources(raw_data_json: dict[str, Any] | None) -> dict[str, str]:
    metadata = _raw_metadata_blob(raw_data_json)
    sources: dict[str, str] = {}
    for field_key, meta_key in ENRICHMENT_FIELD_SOURCE_KEYS.items():
        url = _clean_url(metadata.get(meta_key))
        if url:
            sources[field_key] = url
    return sources

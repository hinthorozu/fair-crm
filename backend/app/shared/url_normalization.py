"""Lightweight URL normalization for optional CRM URL fields."""

from __future__ import annotations


def normalize_optional_url(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if not text.lower().startswith(("http://", "https://")):
        text = f"https://{text}"
    return text

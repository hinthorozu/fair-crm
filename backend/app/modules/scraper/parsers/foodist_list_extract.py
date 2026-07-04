"""Extract Foodist brand list row text from HTML without logo placeholder noise."""

from __future__ import annotations

import re
from html import unescape

# brand-logo is a sibling of brand-info; flattening the whole link duplicates initials.
_BRAND_INFO_AND_LOCATION_RE = re.compile(
    r'<div class="brand-info">(.*?)</div>\s*<div class="brand-location-info">(.*?)</div>\s*<div class="fair-logo-container">',
    re.IGNORECASE | re.DOTALL,
)
_BRAND_NAME_RE = re.compile(
    r'<h2[^>]*class="brand-name"[^>]*>(.*?)</h2>',
    re.IGNORECASE | re.DOTALL,
)


def html_fragment_to_text(fragment: str) -> str:
    plain = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(unescape(plain).split())


def extract_list_text_from_brand_link_html(inner_html: str) -> str:
    """Build list parser input from a brand link's inner HTML.

    Prefer structured ``brand-info`` + ``brand-location-info`` sections so
    ``brand-logo-placeholder`` initials (e.g. ``AB``, ``AK``) are excluded.
    """
    match = _BRAND_INFO_AND_LOCATION_RE.search(inner_html)
    if match:
        info_text = html_fragment_to_text(match.group(1))
        location_text = html_fragment_to_text(match.group(2))
        parts = [part for part in (info_text, location_text) if part]
        if parts:
            return " ".join(parts)

    return html_fragment_to_text(inner_html)


def extract_company_name_from_brand_link_html(inner_html: str) -> str | None:
    """Return the ``h2.brand-name`` text when present."""
    match = _BRAND_NAME_RE.search(inner_html)
    if not match:
        return None
    name = html_fragment_to_text(match.group(1))
    return name or None

"""Tenant-owned quote-template logo storage helpers."""

from __future__ import annotations

import base64
from pathlib import Path
from uuid import UUID

LOGO_STORAGE_ROOT = Path("data/images/quote-template-logos")
LOGO_LEGACY_PREFIX = "/data/quote-template-logos/"
LOGO_API_PREFIX = "/api/v1/data/quote-template-logos/"

LOGO_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
}


def normalize_logo_url(value: str | None) -> str | None:
    if not value:
        return value
    if value.startswith(LOGO_LEGACY_PREFIX):
        return f"{LOGO_API_PREFIX}{value[len(LOGO_LEGACY_PREFIX):]}"
    return value


def _safe_filename(filename: str) -> bool:
    candidate = Path(filename)
    return (
        filename == candidate.name
        and filename not in {".", ".."}
        and candidate.suffix.lower() in LOGO_MEDIA_TYPES
    )


def resolve_logo_file(
    organization_id: UUID,
    filename: str,
    *,
    storage_root: Path | None = None,
) -> Path | None:
    """Resolve one tenant-owned logo path, rejecting traversal and unsupported files."""
    if not _safe_filename(filename):
        return None
    root = (storage_root or LOGO_STORAGE_ROOT).resolve()
    organization_root = (root / str(organization_id)).resolve()
    candidate = (organization_root / filename).resolve()
    if not candidate.is_relative_to(organization_root):
        return None
    return candidate


def owned_logo_file_from_url(
    value: str | None,
    organization_id: UUID,
    *,
    storage_root: Path | None = None,
) -> Path | None:
    """Resolve a managed logo URL only when it belongs to the authoritative organization."""
    normalized = normalize_logo_url(value)
    if not normalized or not normalized.startswith(LOGO_API_PREFIX):
        return None
    relative = normalized[len(LOGO_API_PREFIX):]
    organization_token, separator, filename = relative.partition("/")
    if not separator or organization_token != str(organization_id):
        return None
    return resolve_logo_file(organization_id, filename, storage_root=storage_root)


def validate_logo_url_ownership(value: str | None, organization_id: UUID) -> str | None:
    """Normalize managed URLs and reject managed pointers into another organization."""
    normalized = normalize_logo_url(value)
    if not normalized:
        return normalized
    if not normalized.startswith(LOGO_API_PREFIX):
        # Existing non-managed URLs remain supported; this helper only owns local assets.
        return normalized
    if owned_logo_file_from_url(normalized, organization_id) is None:
        raise ValueError("Quote template logo does not belong to organization")
    return normalized


def logo_src_for_render(value: str | None, organization_id: UUID) -> str:
    """Inline tenant-owned local logos so rendered quote HTML never needs a public file mount."""
    normalized = normalize_logo_url(value)
    if not normalized:
        return ""
    if not normalized.startswith(LOGO_API_PREFIX):
        return normalized

    path = owned_logo_file_from_url(normalized, organization_id)
    if path is None or not path.is_file():
        return ""
    media_type = LOGO_MEDIA_TYPES.get(path.suffix.lower())
    if media_type is None:
        return ""
    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return ""
    return f"data:{media_type};base64,{encoded}"

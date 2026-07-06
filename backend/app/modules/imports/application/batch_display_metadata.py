"""Resolve display metadata (fair name, adapter key) for import batch API responses."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from app.modules.fairs.domain.ports import FairRepository
from app.modules.imports.domain.entities import ImportBatch

_UUID_SUFFIX_PATTERN = re.compile(
    r"^(.+)-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.json$",
    re.IGNORECASE,
)


def resolve_adapter_key_from_batch_preview(raw_preview_json: dict[str, Any] | None) -> str | None:
    preview = raw_preview_json or {}
    source = preview.get("canonical_source") or {}
    adapter_key = source.get("adapter_key")
    return str(adapter_key).strip() if adapter_key else None


def resolve_adapter_key_from_file_name(file_name: str) -> str | None:
    match = _UUID_SUFFIX_PATTERN.match((file_name or "").strip())
    if match is None:
        return None
    prefix = match.group(1).strip()
    return prefix or None


def resolve_adapter_key_from_batch(batch: ImportBatch) -> str | None:
    adapter_key = resolve_adapter_key_from_batch_preview(batch.raw_preview_json)
    if adapter_key:
        return adapter_key
    return resolve_adapter_key_from_file_name(batch.file_name)


def resolve_fair_name(
    fair_repository: FairRepository,
    *,
    organization_id: UUID,
    fair_id: UUID | None,
) -> str | None:
    if fair_id is None:
        return None
    fair = fair_repository.get_by_id(organization_id, fair_id)
    return fair.name if fair is not None else None


def build_fair_name_lookup(
    fair_repository: FairRepository,
    *,
    organization_id: UUID,
    fair_ids: set[UUID],
) -> dict[UUID, str]:
    lookup: dict[UUID, str] = {}
    for fair_id in fair_ids:
        fair = fair_repository.get_by_id(organization_id, fair_id)
        if fair is not None:
            lookup[fair_id] = fair.name
    return lookup

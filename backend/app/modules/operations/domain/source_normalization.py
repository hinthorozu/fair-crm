"""Normalize Operation source selection helpers."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.operations.domain.exceptions import InvalidOperationConfigError, InvalidSourceKindError
from app.modules.operations.domain.value_objects import SourceKind


def parse_source_ids(raw: Any) -> list[UUID]:
    """Parse source_ids from API/config payloads into UUIDs."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise InvalidOperationConfigError("source_ids must be a list of UUIDs")

    parsed: list[UUID] = []
    seen: set[UUID] = set()
    for index, item in enumerate(raw):
        try:
            value = item if isinstance(item, UUID) else UUID(str(item))
        except (TypeError, ValueError) as exc:
            raise InvalidOperationConfigError(
                f"source_ids[{index}] is not a valid UUID"
            ) from exc
        if value in seen:
            continue
        seen.add(value)
        parsed.append(value)
    return parsed


def extract_source_ids(source_config: dict[str, Any] | None) -> list[UUID]:
    """Read canonical source_ids, with legacy fair_id / fair_ids fallback."""
    config = dict(source_config or {})
    if "source_ids" in config:
        return parse_source_ids(config.get("source_ids"))

    legacy_ids: list[Any] = []
    if "fair_ids" in config and isinstance(config.get("fair_ids"), list):
        legacy_ids.extend(config["fair_ids"])
    fair_id = config.get("fair_id")
    if fair_id is not None:
        legacy_ids.append(fair_id)
    return parse_source_ids(legacy_ids)


def normalize_source_kind(source_kind: str) -> str:
    """Map deprecated source kinds onto the canonical set."""
    if source_kind == "multiple_fairs":
        return SourceKind.FAIR
    try:
        return SourceKind(source_kind)
    except ValueError as exc:
        raise InvalidSourceKindError(f"Invalid source kind: {source_kind}") from exc


def build_normalized_source_config(
    *,
    source_kind: str,
    source_ids: list[UUID] | None,
    source_config: dict[str, Any] | None,
) -> tuple[str, dict[str, Any], list[UUID]]:
    """
    Normalize source_kind + source_ids into persisted shape.

    Fair sources always store:
      source_kind = fair
      source_config.source_ids = [uuid, ...]
    """
    kind = normalize_source_kind(source_kind)
    config = dict(source_config or {})

    # Prefer non-empty top-level source_ids; otherwise read config/legacy keys.
    if source_ids:
        ids = parse_source_ids(source_ids)
    else:
        ids = extract_source_ids(config)

    # Drop legacy fair keys; keep unrelated keys (e.g. customer_id for other sources).
    config.pop("fair_id", None)
    config.pop("fair_ids", None)
    config.pop("source_ids", None)

    if kind == SourceKind.FAIR:
        if not ids:
            raise InvalidOperationConfigError(
                "source_ids is required and must not be empty when source_kind is fair"
            )
        config["source_ids"] = [str(item) for item in ids]
        return kind, config, ids

    if ids:
        raise InvalidOperationConfigError(
            f"source_ids is only allowed when source_kind is fair (got {kind})"
        )
    return kind, config, []

"""Validate canonical import documents."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.shared.canonical_import.schema import CanonicalImportDocument


class CanonicalImportValidationError(ValueError):
    """Raised when a payload does not match the canonical import schema."""


def validate_canonical_import(data: dict[str, Any] | CanonicalImportDocument) -> CanonicalImportDocument:
    if isinstance(data, CanonicalImportDocument):
        return data
    try:
        return CanonicalImportDocument.model_validate(data)
    except ValidationError as exc:
        raise CanonicalImportValidationError(str(exc)) from exc

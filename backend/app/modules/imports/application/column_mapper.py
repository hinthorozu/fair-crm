"""Manual column mapping for Smart Import Wizard."""

from typing import Any

from app.modules.imports.domain.exceptions import InvalidColumnMappingError
from app.modules.imports.domain.services.header_mapping import (
    HEADER_ALIASES,
    map_header_to_field,
    normalize_header,
)

WIZARD_MAPPING_FIELDS = frozenset(
    {
        "company_name",
        "email",
        "phone",
        "mobile_phone",
        "website",
        "country",
        "city",
        "address",
        "tax_number",
        "contact_first_name",
        "contact_last_name",
        "contact_title",
        "contact_department",
        "contact_email",
        "contact_phone",
        "contact_mobile_phone",
        "notes",
        "hall",
        "stand",
    }
)

REJECTED_MAPPING_FIELDS = frozenset({"fair_name"})


def _column_letter(index: int) -> str:
    from openpyxl.utils import get_column_letter

    return get_column_letter(index + 1)


def suggest_column_mapping(
    raw_preview: dict[str, Any],
    *,
    has_header_row: bool | None = None,
) -> dict[str, Any]:
    detected = raw_preview.get("detected_headers") or []
    auto_header = _detect_has_header(detected)
    use_header = auto_header if has_header_row is None else has_header_row

    mappings: dict[str, dict[str, Any]] = {}
    if use_header and detected:
        for index, header in enumerate(detected):
            if header is None:
                continue
            field = map_header_to_field(str(header))
            if field and field in WIZARD_MAPPING_FIELDS and field not in mappings:
                mappings[field] = {"type": "column_index", "value": index}

    return {
        "has_header_row": use_header,
        "mappings": mappings,
    }


def _detect_has_header(headers: list[Any]) -> bool:
    if not headers:
        return False
    mapped = 0
    for header in headers:
        if header is None:
            continue
        if map_header_to_field(str(header)):
            mapped += 1
    return mapped >= 2


def validate_column_mapping(mapping_config: dict[str, Any]) -> None:
    mappings = mapping_config.get("mappings") or {}
    if not isinstance(mappings, dict):
        raise InvalidColumnMappingError("Invalid mapping format")

    for field in mappings:
        if field in REJECTED_MAPPING_FIELDS:
            raise InvalidColumnMappingError(f"Field '{field}' is not supported")
        if field not in WIZARD_MAPPING_FIELDS:
            raise InvalidColumnMappingError(f"Unknown mapping field: {field}")

    if "company_name" not in mappings:
        raise InvalidColumnMappingError("company_name mapping is required")

    seen_columns: set[int] = set()
    for field, spec in mappings.items():
        if not isinstance(spec, dict):
            raise InvalidColumnMappingError(f"Invalid mapping spec for {field}")
        if spec.get("type") != "column_index":
            raise InvalidColumnMappingError(f"Unsupported mapping type for {field}")
        try:
            col_index = int(spec["value"])
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidColumnMappingError(f"Invalid column index for {field}") from exc
        if col_index in seen_columns:
            raise InvalidColumnMappingError(f"Duplicate column mapping at index {col_index}")
        seen_columns.add(col_index)
        _ = field


def apply_column_mapping(
    raw_preview: dict[str, Any],
    mapping_config: dict[str, Any],
) -> list[dict[str, Any]]:
    validate_column_mapping(mapping_config)
    rows: list[list[Any]] = raw_preview.get("rows") or []
    has_header = bool(mapping_config.get("has_header_row"))
    mappings: dict[str, dict[str, Any]] = mapping_config.get("mappings") or {}

    data_rows = rows[1:] if has_header and rows else rows
    mapped_rows: list[dict[str, Any]] = []

    for row in data_rows:
        raw: dict[str, Any] = {}
        for field, spec in mappings.items():
            index = int(spec["value"])
            if index < len(row):
                value = row[index]
                if value is not None and str(value).strip():
                    raw[field] = value
        if raw:
            mapped_rows.append(raw)

    return mapped_rows


def build_mapping_field_options(raw_preview: dict[str, Any], has_header_row: bool) -> list[dict[str, Any]]:
    columns = raw_preview.get("columns") or []
    headers = raw_preview.get("detected_headers") or []
    options: list[dict[str, Any]] = []
    for col in columns:
        index = col["index"]
        label = f"Kolon {col['letter']}"
        if has_header_row and index < len(headers) and headers[index]:
            label = f"{headers[index]} ({col['letter']})"
        options.append({"index": index, "letter": col["letter"], "label": label})
    return options

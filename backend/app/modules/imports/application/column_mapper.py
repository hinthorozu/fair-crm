"""Manual column mapping for Universal Import Engine."""

from typing import Any

from app.modules.imports.domain.exceptions import InvalidColumnMappingError
from app.modules.imports.domain.services.header_mapping import map_header_to_field, normalize_header
from app.modules.imports.domain.value_objects import ExcelHeaderMode

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


def header_mode_to_has_header(mode: ExcelHeaderMode) -> bool:
    return mode != ExcelHeaderMode.NO_HEADER


def resolve_header_mode(
    *,
    header_mode: ExcelHeaderMode | None = None,
    has_header_row: bool | None = None,
) -> ExcelHeaderMode:
    if header_mode is not None:
        return header_mode
    if has_header_row is False:
        return ExcelHeaderMode.NO_HEADER
    return ExcelHeaderMode.FIRST_ROW_HEADER


def resolve_header_row_index(
    mode: ExcelHeaderMode,
    *,
    header_row_index: int | None = None,
) -> int | None:
    if mode == ExcelHeaderMode.NO_HEADER:
        return None
    if mode == ExcelHeaderMode.MANUAL_HEADER_ROW:
        if header_row_index is None or header_row_index < 0:
            raise InvalidColumnMappingError("header_row_index is required for manual_header_row mode")
        return header_row_index
    return 0


def _headers_for_mode(
    raw_preview: dict[str, Any],
    mode: ExcelHeaderMode,
    header_row_index: int | None,
) -> list[Any]:
    rows: list[list[Any]] = raw_preview.get("rows") or []
    if mode == ExcelHeaderMode.NO_HEADER:
        return []
    index = header_row_index if header_row_index is not None else 0
    if index >= len(rows):
        return []
    return [str(v) if v is not None else None for v in rows[index]]


def suggest_column_mapping(
    raw_preview: dict[str, Any],
    *,
    has_header_row: bool | None = None,
    header_mode: ExcelHeaderMode | None = None,
) -> dict[str, Any]:
    mode = resolve_header_mode(header_mode=header_mode, has_header_row=has_header_row)
    header_row_index = resolve_header_row_index(mode)
    headers = _headers_for_mode(raw_preview, mode, header_row_index)

    mappings: dict[str, dict[str, Any]] = {}
    if mode != ExcelHeaderMode.NO_HEADER and headers:
        for index, header in enumerate(headers):
            if header is None:
                continue
            field = map_header_to_field(str(header))
            if field and field in WIZARD_MAPPING_FIELDS and field not in mappings:
                mappings[field] = {"type": "column_index", "value": index}

    return {
        "header_mode": mode.value,
        "has_header_row": header_mode_to_has_header(mode),
        "header_row_index": header_row_index,
        "mappings": mappings,
    }


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
    mode = resolve_header_mode(
        header_mode=ExcelHeaderMode(mapping_config["header_mode"])
        if mapping_config.get("header_mode")
        else None,
        has_header_row=mapping_config.get("has_header_row"),
    )
    header_row_index = mapping_config.get("header_row_index")
    if header_row_index is None and mode != ExcelHeaderMode.NO_HEADER:
        header_row_index = 0

    if mode == ExcelHeaderMode.NO_HEADER:
        data_rows = rows
    else:
        start = int(header_row_index or 0) + 1
        data_rows = rows[start:] if start <= len(rows) else []

    mappings: dict[str, dict[str, Any]] = mapping_config.get("mappings") or {}
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


def build_mapping_field_options(
    raw_preview: dict[str, Any],
    *,
    has_header_row: bool | None = None,
    header_mode: ExcelHeaderMode | None = None,
    header_row_index: int | None = None,
) -> list[dict[str, Any]]:
    mode = resolve_header_mode(header_mode=header_mode, has_header_row=has_header_row)
    resolved_index = resolve_header_row_index(mode, header_row_index=header_row_index)
    headers = _headers_for_mode(raw_preview, mode, resolved_index)
    columns = raw_preview.get("columns") or []
    options: list[dict[str, Any]] = []

    for col in columns:
        index = col["index"]
        letter = col["letter"]
        sample_values = col.get("sample_values") or []
        if mode == ExcelHeaderMode.NO_HEADER:
            samples = ", ".join(str(v) for v in sample_values[:3])
            label = f"Column {letter}"
            if samples:
                label = f"Column {letter} ({samples})"
        elif index < len(headers) and headers[index]:
            label = f"{headers[index]} ({letter})"
        else:
            label = f"Column {letter}"
        options.append(
            {
                "index": index,
                "letter": letter,
                "label": label,
                "sample_values": sample_values,
            }
        )
    return options

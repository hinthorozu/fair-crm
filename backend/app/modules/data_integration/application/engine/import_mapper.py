from typing import Any

from app.modules.imports.application.column_mapper import (
    apply_column_mapping,
    build_mapping_field_options,
    suggest_column_mapping,
    validate_column_mapping,
)
from app.modules.imports.domain.value_objects import ExcelHeaderMode


class ImportMapper:
    """Maps source columns to canonical CRM import fields."""

    suggest = staticmethod(suggest_column_mapping)
    validate = staticmethod(validate_column_mapping)
    apply = staticmethod(apply_column_mapping)
    build_options = staticmethod(build_mapping_field_options)


class ImportParser:
    """Parses adapter output — delegates to source adapters."""

    @staticmethod
    def headers_for_preview(raw_preview: dict[str, Any], header_mode: ExcelHeaderMode) -> list[Any]:
        from app.modules.imports.application.column_mapper import _headers_for_mode, resolve_header_row_index

        index = resolve_header_row_index(header_mode)
        return _headers_for_mode(raw_preview, header_mode, index)

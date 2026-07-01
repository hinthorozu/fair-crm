from typing import Any

from app.modules.imports.application.excel_parser import parse_xlsx_rows
from app.modules.imports.domain.exceptions import InvalidImportFileError
from app.modules.imports.domain.value_objects import ImportSourceType


class ExcelImportSourceAdapter:
    """Excel (.xlsx) import source — v1 production adapter."""

    source_type = ImportSourceType.EXCEL

    def extract_rows(self, payload: bytes, *, file_name: str) -> list[dict[str, Any]]:
        if not file_name.lower().endswith(".xlsx"):
            raise InvalidImportFileError("Only .xlsx files are supported")
        return parse_xlsx_rows(payload)

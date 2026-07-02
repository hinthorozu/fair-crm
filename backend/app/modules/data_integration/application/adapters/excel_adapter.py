"""Excel Source Adapter — first Universal Data Integration adapter."""

from typing import Any

from app.modules.data_integration.domain.source_adapter import RawSourceData, SourceConnection
from app.modules.imports.application.raw_excel_parser import parse_xlsx_raw
from app.modules.imports.domain.exceptions import InvalidImportFileError
from app.modules.imports.domain.value_objects import ImportSourceType


class ExcelSourceAdapter:
    """Reads .xlsx workbooks; Import Engine handles mapping, matching, and apply."""

    @property
    def source_type(self) -> ImportSourceType:
        return ImportSourceType.EXCEL

    def connect(self, connection: SourceConnection) -> None:
        name = (connection.file_name or "").lower()
        if not name.endswith(".xlsx"):
            raise InvalidImportFileError("Only .xlsx files are supported")
        if not connection.payload:
            raise InvalidImportFileError("Excel file is empty")

    def read_source(
        self,
        connection: SourceConnection,
        *,
        sheet_name: str | None = None,
    ) -> RawSourceData:
        parsed = parse_xlsx_raw(connection.payload, sheet_name=sheet_name)
        return RawSourceData(
            columns=parsed["columns"],
            rows=parsed["rows"],
            total_rows=parsed["total_rows"],
            detected_headers=parsed["detected_headers"],
            sheet_name=parsed.get("sheet_name"),
            available_sheets=parsed.get("available_sheets") or [],
            metadata={"source_type": self.source_type.value},
        )

    def normalize(self, raw: RawSourceData) -> dict[str, Any]:
        return {
            "columns": raw.columns,
            "rows": raw.rows,
            "total_rows": raw.total_rows,
            "detected_headers": raw.detected_headers,
            "sheet_name": raw.sheet_name,
            "available_sheets": raw.available_sheets,
            "metadata": raw.metadata,
        }

    def preview(
        self,
        connection: SourceConnection,
        *,
        sheet_name: str | None = None,
    ) -> dict[str, Any]:
        self.connect(connection)
        raw = self.read_source(connection, sheet_name=sheet_name)
        return self.normalize(raw)


# Backward-compatible alias used by Sprint 09.1 engine package
ExcelImportAdapter = ExcelSourceAdapter


def get_excel_adapter() -> ExcelSourceAdapter:
    return ExcelSourceAdapter()

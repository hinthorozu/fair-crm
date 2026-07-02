"""Tests for Universal Source Adapter framework (Sprint 09.2)."""

from io import BytesIO

from openpyxl import Workbook

from app.modules.data_integration.application.adapters.excel_adapter import ExcelSourceAdapter
from app.modules.data_integration.application.adapters.registry import SourceAdapterRegistry
from app.modules.data_integration.domain.source_adapter import SourceConnection
from app.modules.imports.domain.exceptions import InvalidImportFileError
from app.modules.imports.domain.value_objects import ImportSourceType


def _xlsx(rows: list[list[str]], headers: list[str] | None = None) -> bytes:
    wb = Workbook()
    ws = wb.active
    if headers:
        ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_excel_adapter_lifecycle():
    adapter = ExcelSourceAdapter()
    assert adapter.source_type == ImportSourceType.EXCEL

    content = _xlsx([["Acme", "a@test.com"]])
    connection = SourceConnection(payload=content, file_name="test.xlsx")
    adapter.connect(connection)
    raw = adapter.read_source(connection)
    assert raw.total_rows == 1

    preview = adapter.preview(connection)
    assert preview["total_rows"] == 1
    assert preview["columns"]


def test_registry_resolves_excel_by_extension():
    registry = SourceAdapterRegistry()
    registry.register(ExcelSourceAdapter(), file_extensions=(".xlsx",))

    adapter = registry.get_for_file("participants.xlsx")
    assert adapter.source_type == ImportSourceType.EXCEL
    assert ImportSourceType.EXCEL in registry.list_source_types()


def test_registry_rejects_unknown_extension():
    registry = SourceAdapterRegistry()
    registry.register(ExcelSourceAdapter(), file_extensions=(".xlsx",))

    try:
        registry.get_for_file("data.csv")
        assert False, "expected InvalidImportFileError"
    except InvalidImportFileError:
        pass

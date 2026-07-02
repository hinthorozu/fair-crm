"""Re-export Excel adapter from adapters package (Sprint 09.2 migration)."""

from app.modules.data_integration.application.adapters.excel_adapter import (
    ExcelImportAdapter,
    ExcelSourceAdapter,
    get_excel_adapter,
)

__all__ = ["ExcelImportAdapter", "ExcelSourceAdapter", "get_excel_adapter"]

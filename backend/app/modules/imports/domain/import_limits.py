"""Configurable safety limits for Excel import uploads and analyze."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.imports.domain.exceptions import InvalidImportFileError


def format_limit_number(value: int) -> str:
    """Turkish-style thousands separator (50.000)."""
    return f"{value:,}".replace(",", ".")


def row_limit_exceeded_message(max_rows: int) -> str:
    return f"Dosya çok büyük. Maksimum {format_limit_number(max_rows)} satır desteklenmektedir."


def column_limit_exceeded_message(max_columns: int) -> str:
    return f"Dosya çok büyük. Maksimum {format_limit_number(max_columns)} kolon desteklenmektedir."


def sheet_limit_exceeded_message(max_sheets: int) -> str:
    return f"Dosya çok büyük. Maksimum {format_limit_number(max_sheets)} sayfa desteklenmektedir."


def file_size_limit_exceeded_message(max_file_size_mb: int) -> str:
    return f"Dosya çok büyük. Maksimum {max_file_size_mb} MB desteklenmektedir."


@dataclass(frozen=True)
class ImportLimits:
    max_file_size_bytes: int
    max_rows: int
    max_columns: int
    max_sheets: int
    mapping_sample_rows: int
    grid_preview_rows: int
    analyze_chunk_size: int

    @classmethod
    def from_settings(cls, settings: object) -> ImportLimits:
        max_file_size_mb = int(getattr(settings, "import_max_file_size_mb", 50))
        return cls(
            max_file_size_bytes=max_file_size_mb * 1024 * 1024,
            max_rows=int(getattr(settings, "import_max_rows", 50_000)),
            max_columns=int(getattr(settings, "import_max_columns", 100)),
            max_sheets=int(getattr(settings, "import_max_sheets", 20)),
            mapping_sample_rows=int(getattr(settings, "import_mapping_sample_rows", 10)),
            grid_preview_rows=int(getattr(settings, "import_grid_preview_rows", 50)),
            analyze_chunk_size=int(getattr(settings, "import_analyze_chunk_size", 500)),
        )

    def validate_file_size(self, size_bytes: int) -> None:
        if size_bytes > self.max_file_size_bytes:
            max_mb = self.max_file_size_bytes // (1024 * 1024)
            raise InvalidImportFileError(file_size_limit_exceeded_message(max_mb))

    def validate_sheet_count(self, sheet_count: int) -> None:
        if sheet_count > self.max_sheets:
            raise InvalidImportFileError(sheet_limit_exceeded_message(self.max_sheets))

    def validate_column_count(self, column_count: int) -> None:
        if column_count > self.max_columns:
            raise InvalidImportFileError(column_limit_exceeded_message(self.max_columns))

    def validate_row_count(self, row_count: int) -> None:
        if row_count > self.max_rows:
            raise InvalidImportFileError(row_limit_exceeded_message(self.max_rows))

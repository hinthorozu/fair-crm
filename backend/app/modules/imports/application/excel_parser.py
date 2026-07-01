from io import BytesIO
from typing import Any

from openpyxl import load_workbook

from app.modules.imports.domain.exceptions import InvalidImportFileError
from app.modules.imports.domain.services.header_mapping import map_header_to_field


def parse_xlsx_rows(file_content: bytes) -> list[dict[str, Any]]:
    try:
        workbook = load_workbook(filename=BytesIO(file_content), read_only=True, data_only=True)
    except Exception as exc:
        raise InvalidImportFileError("Invalid xlsx file") from exc

    sheet = workbook.active
    if sheet is None:
        raise InvalidImportFileError("Worksheet is empty")

    rows_iter = sheet.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration as exc:
        raise InvalidImportFileError("Worksheet has no header row") from exc

    field_indexes: dict[int, str] = {}
    for index, header in enumerate(header_row):
        if header is None:
            continue
        field = map_header_to_field(str(header))
        if field:
            field_indexes[index] = field

    if "company_name" not in field_indexes.values():
        raise InvalidImportFileError("Required column company_name (Firma Adı) not found")

    parsed_rows: list[dict[str, Any]] = []
    for row in rows_iter:
        if row is None or all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        raw: dict[str, Any] = {}
        for index, field in field_indexes.items():
            if index < len(row):
                value = row[index]
                if value is not None and str(value).strip():
                    raw[field] = value
        if raw:
            parsed_rows.append(raw)

    workbook.close()
    return parsed_rows

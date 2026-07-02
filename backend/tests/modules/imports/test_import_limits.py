"""Tests for import upload safety limits."""

from io import BytesIO

import pytest
from openpyxl import Workbook

from app.core.config import get_settings
from app.modules.imports.application.raw_excel_parser import parse_xlsx_raw
from app.modules.imports.domain.exceptions import InvalidImportFileError
from app.modules.imports.domain.import_limits import ImportLimits, row_limit_exceeded_message


def _strict_limits() -> ImportLimits:
    return ImportLimits(
        max_file_size_bytes=1024 * 1024,
        max_rows=5,
        max_columns=3,
        max_sheets=2,
        mapping_sample_rows=10,
        grid_preview_rows=50,
        analyze_chunk_size=2,
    )


def _build_xlsx(
    *,
    data_rows: int = 1,
    columns: int = 2,
    sheets: int = 1,
) -> bytes:
    workbook = Workbook()
    for index in range(1, sheets):
        workbook.create_sheet(title=f"Sheet{index + 1}")
    worksheet = workbook.active
    assert worksheet is not None
    worksheet.title = "Data"
    header = [f"Col{i + 1}" for i in range(columns)]
    if columns > 0:
        header[0] = "Firma Adı"
    worksheet.append(header)
    for row_index in range(data_rows):
        worksheet.append([f"Company {row_index}"] + [f"v{row_index}-{i}" for i in range(columns - 1)])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_row_limit_exceeded_message_format():
    assert row_limit_exceeded_message(50_000) == "Dosya çok büyük. Maksimum 50.000 satır desteklenmektedir."


def test_parse_rejects_too_many_rows():
    limits = _strict_limits()
    content = _build_xlsx(data_rows=6, columns=2, sheets=1)
    with pytest.raises(InvalidImportFileError, match="5 satır"):
        parse_xlsx_raw(content, limits=limits)


def test_parse_rejects_too_many_columns():
    limits = _strict_limits()
    content = _build_xlsx(data_rows=1, columns=4, sheets=1)
    with pytest.raises(InvalidImportFileError, match="3 kolon"):
        parse_xlsx_raw(content, limits=limits)


def test_parse_rejects_too_many_sheets():
    limits = _strict_limits()
    content = _build_xlsx(data_rows=1, columns=2, sheets=3)
    with pytest.raises(InvalidImportFileError, match="2 sayfa"):
        parse_xlsx_raw(content, limits=limits)


def test_parse_rejects_oversized_file():
    limits = _strict_limits()
    content = _build_xlsx(data_rows=1, columns=2, sheets=1)
    with pytest.raises(InvalidImportFileError, match="1 MB"):
        limits.validate_file_size(len(content) + limits.max_file_size_bytes)


def test_parse_accepts_within_limits():
    limits = _strict_limits()
    content = _build_xlsx(data_rows=4, columns=2, sheets=1)
    preview = parse_xlsx_raw(content, limits=limits)
    assert preview["total_rows"] == 5  # header + 4 data rows


def _fair_id(client, auth_headers) -> str:
    response = client.post(
        "/api/v1/fairs",
        headers=auth_headers,
        json={"name": "Limit Fair", "location": "Istanbul", "start_date": "2026-06-01", "end_date": "2026-06-03"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_upload_api_rejects_row_limit(client, auth_headers, monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("IMPORT_MAX_ROWS", "3")
    fair_id = _fair_id(client, auth_headers)
    content = _build_xlsx(data_rows=5, columns=2, sheets=1)
    response = client.post(
        "/api/v1/data-integration/imports/upload",
        headers=auth_headers,
        data={"fair_id": str(fair_id)},
        files={"file": ("big.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    get_settings.cache_clear()
    assert response.status_code == 400
    assert "3 satır" in response.json()["detail"]


def test_upload_api_rejects_file_size(client, auth_headers, monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("IMPORT_MAX_FILE_SIZE_MB", "0")
    fair_id = _fair_id(client, auth_headers)
    content = _build_xlsx(data_rows=1, columns=2, sheets=1)
    response = client.post(
        "/api/v1/data-integration/imports/upload",
        headers=auth_headers,
        data={"fair_id": str(fair_id)},
        files={"file": ("big.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    get_settings.cache_clear()
    assert response.status_code == 400
    assert "MB" in response.json()["detail"]

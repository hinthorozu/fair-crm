"""Extract raw email-like tokens from Excel workbooks for bulk-email preview."""

from __future__ import annotations

from io import BytesIO

from openpyxl import load_workbook

from app.modules.fair_emails.application.recipient_resolution import tokenize_email_field
from app.modules.imports.domain.exceptions import InvalidImportFileError


def extract_email_tokens_from_xlsx(content: bytes) -> list[str]:
    """Scan all sheets/cells and return semicolon-split raw tokens (no validation)."""
    if not content:
        raise InvalidImportFileError("Only .xlsx files are supported")

    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001 — openpyxl raises varied parse errors
        raise InvalidImportFileError("Excel dosyası okunamadı") from exc

    tokens: list[str] = []
    try:
        for sheet in workbook.worksheets:
            for row in sheet.iter_rows(values_only=True):
                if row is None:
                    continue
                for cell in row:
                    if cell is None:
                        continue
                    text = str(cell).strip()
                    if not text:
                        continue
                    tokens.extend(tokenize_email_field(text))
    finally:
        workbook.close()

    return tokens

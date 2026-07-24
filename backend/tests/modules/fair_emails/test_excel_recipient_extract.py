"""Excel recipient row extraction for bulk-email wizard."""

from io import BytesIO

from openpyxl import Workbook

from app.modules.fair_emails.application.excel_email_extract import (
    extract_email_tokens_from_xlsx,
    extract_excel_recipient_rows,
)
from app.modules.fair_emails.application.recipient_resolution import resolve_manual_and_excel_emails


def _xlsx_bytes(rows: list[tuple[object, ...]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(list(row))
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_extract_excel_recipient_rows_two_columns():
    content = _xlsx_bytes(
        [
            ("Alıcı / Firma Adı", "E-posta"),
            ("Ahmet Yılmaz", "AHMET@EXAMPLE.COM"),
            ("ERMED TIP MEDİKAL", "INFO@ERMEDMEDICAL.COM.TR"),
        ]
    )
    rows = extract_excel_recipient_rows(content)
    assert len(rows) == 3
    assert rows[0].display_name == "Alıcı / Firma Adı"
    assert rows[0].email == "E-posta"
    assert rows[1].display_name == "Ahmet Yılmaz"
    assert rows[1].email == "AHMET@EXAMPLE.COM"
    assert rows[2].display_name == "ERMED TIP MEDİKAL"
    assert rows[2].email == "INFO@ERMEDMEDICAL.COM.TR"


def test_resolve_excel_rows_sets_display_name_and_normalizes_email():
    result = resolve_manual_and_excel_emails(
        manual_emails_text=None,
        excel_recipient_rows=[
            ("Ahmet Yılmaz", "AHMET@EXAMPLE.COM"),
            ("ERMED TIP MEDİKAL", "INFO@ERMEDMEDICAL.COM.TR"),
        ],
    )
    will_send = [item for item in result.recipients if item.status == "will_send"]
    assert len(will_send) == 2
    by_email = {item.email: item for item in will_send}
    ahmet = by_email["ahmet@example.com"]
    assert ahmet.recipient_name == "Ahmet Yılmaz"
    assert ahmet.company_name == "Ahmet Yılmaz"
    assert ahmet.source == "excel"
    ermed = by_email["info@ermedmedical.com.tr"]
    assert ermed.recipient_name == "ERMED TIP MEDİKAL"
    assert ermed.company_name == "ERMED TIP MEDİKAL"


def test_resolve_excel_skips_header_like_and_invalid_and_dedupes():
    result = resolve_manual_and_excel_emails(
        manual_emails_text=None,
        excel_recipient_rows=[
            ("Alıcı / Firma Adı", "E-posta"),
            ("Ahmet Yılmaz", "AHMET@EXAMPLE.COM"),
            ("Duplicate", "ahmet@example.com"),
            ("Bad", "not-an-email"),
        ],
    )
    assert result.invalid_count == 2  # header email + bad
    assert result.duplicate_count == 1
    assert result.deduped_recipient_count == 1
    will_send = [item for item in result.recipients if item.status == "will_send"]
    assert will_send[0].email == "ahmet@example.com"
    assert will_send[0].recipient_name == "Ahmet Yılmaz"


def test_resolve_manual_semicolon_unchanged_with_excel_rows():
    result = resolve_manual_and_excel_emails(
        manual_emails_text="one@example.com; two@example.com",
        excel_recipient_rows=[("Excel Co", "three@example.com")],
    )
    assert result.deduped_recipient_count == 3
    sources = {item.email: item.source for item in result.recipients if item.status == "will_send"}
    assert sources["one@example.com"] == "manual"
    assert sources["two@example.com"] == "manual"
    assert sources["three@example.com"] == "excel"


def test_legacy_extract_email_tokens_returns_col2_only():
    content = _xlsx_bytes([("Name", "a@example.com"), ("Other", "b@example.com")])
    assert extract_email_tokens_from_xlsx(content) == ["a@example.com", "b@example.com"]

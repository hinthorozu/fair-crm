"""Unit tests for column mapping preview (Sprint 09.3)."""

from app.modules.imports.application.column_mapper import (
    MAX_MAPPING_SAMPLE_ROWS,
    build_mapping_preview_columns,
)
from app.modules.imports.domain.value_objects import ExcelHeaderMode


def _raw_preview(rows: list[list]) -> dict:
    from openpyxl.utils import get_column_letter

    max_cols = max(len(r) for r in rows)
    columns = [
        {"index": i, "letter": get_column_letter(i + 1), "sample_values": []}
        for i in range(max_cols)
    ]
    return {
        "rows": rows,
        "columns": columns,
        "detected_headers": [str(v) if v else None for v in rows[0]],
    }


def test_first_row_header_samples_skip_header_row():
    preview = _raw_preview(
        [
            ["Firma", "Telefon"],
            ["ABC Mobilya", "0212 555 44 33"],
            ["XYZ Plastik", "0532 111 22 33"],
            [None, "empty phone"],
        ]
    )
    columns = build_mapping_preview_columns(preview, header_mode=ExcelHeaderMode.FIRST_ROW_HEADER)
    assert columns[0]["header"] == "Firma"
    assert columns[0]["samples"][0] == "ABC Mobilya"
    assert columns[1]["samples"][0] == "0212 555 44 33"
    assert columns[1]["samples"][1] == "0532 111 22 33"


def test_no_header_uses_column_letters_and_data_rows():
    preview = _raw_preview(
        [
            ["ABC Mobilya", "0212 555"],
            ["XYZ Plastik", None],
        ]
    )
    columns = build_mapping_preview_columns(preview, header_mode=ExcelHeaderMode.NO_HEADER)
    assert columns[0]["header"] is None
    assert columns[0]["key"] == "A"
    assert columns[0]["samples"][0] == "ABC Mobilya"
    assert columns[1]["samples"][1] is None


def test_manual_header_row_uses_selected_row_as_header():
    preview = _raw_preview(
        [
            ["skip", "skip"],
            ["Firma", "Email"],
            ["Acme", "a@test.com"],
        ]
    )
    columns = build_mapping_preview_columns(
        preview,
        header_mode=ExcelHeaderMode.MANUAL_HEADER_ROW,
        header_row_index=1,
    )
    assert columns[0]["header"] == "Firma"
    assert columns[0]["samples"] == ["Acme"]
    assert columns[1]["samples"] == ["a@test.com"]


def test_samples_capped_at_max_rows():
    rows = [["H"]] + [[f"Row {i}"] for i in range(15)]
    preview = _raw_preview(rows)
    columns = build_mapping_preview_columns(preview, header_mode=ExcelHeaderMode.FIRST_ROW_HEADER)
    assert len(columns[0]["samples"]) == MAX_MAPPING_SAMPLE_ROWS


def test_column_stats_computed():
    preview = _raw_preview([["Firma"], ["ABC"], [None], ["XYZ"]])
    columns = build_mapping_preview_columns(preview, header_mode=ExcelHeaderMode.FIRST_ROW_HEADER)
    stats = columns[0]["stats"]
    assert stats["total"] == 3
    assert stats["empty"] == 1
    assert stats["filled"] == 2
    assert stats["first_value"] == "ABC"

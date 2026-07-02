# Universal Import Mapping Preview Standard

**Status:** Accepted (Sprint 09.3)  
**ADR:** [ADR-024](../DECISIONS.md)  
**Related:** [IMPORT_ARCHITECTURE.md](IMPORT_ARCHITECTURE.md), [IMPORT_WIZARD_UX_FLOW.md](../IMPORT_WIZARD_UX_FLOW.md)

---

## Purpose

Before column mapping is saved, users must answer: **"What does this column actually contain?"**

Header names alone are insufficient for:

- Headerless files (columns A/B/C)
- Incorrect or misleading headers
- Duplicate or ambiguous column names

This standard defines how **sample values** are produced server-side and displayed in the mapping UI.

---

## UI Layout (3 columns)

| CRM Alanı | Kaynak Kolonu | Kaynak Önizleme |
|-----------|---------------|-----------------|
| Firma Adı | Firma (A) ▼   | ABC Mobilya, XYZ Plastik, … |
| Telefon   | Telefon (B) ▼ | 0212 555 44 33, … |

- **Live preview:** When the source column dropdown changes, the preview column updates immediately.
- **Default rows:** 3 sample values visible.
- **Expand:** "Diğer örnekleri göster" reveals up to **10** rows total.
- **Empty cells:** Rendered as `—`.
- **Long values:** Truncated with full value in hover tooltip.
- **Column stats:** Small footer per preview — total, empty, filled, first value.

---

## Header Modes

| Mode | Column label | Sample source |
|------|--------------|---------------|
| `first_row_header` | Header text + letter | Rows after row 0 |
| `no_header` | Column A/B/C… | First data rows (including row 0) |
| `manual_header_row` | Header from selected row | Rows after selected header row |

---

## API Contract

### Upload response (`POST …/upload`)

Includes `mapping_columns` using the default suggested header mode:

```json
{
  "mapping_columns": [
    {
      "key": "A",
      "index": 0,
      "letter": "A",
      "header": "Firma",
      "samples": ["ABC Mobilya", "XYZ Plastik", null],
      "stats": {
        "total": 3,
        "empty": 1,
        "filled": 2,
        "first_value": "ABC Mobilya"
      }
    }
  ]
}
```

### Mapping preview (`GET …/{batch_id}/mapping-preview`)

Query parameters:

- `header_mode` — optional; `first_row_header` | `no_header` | `manual_header_row`
- `header_row_index` — required for `manual_header_row` (0-based)

Returns the same `columns` array shape. Used when the user changes header mode or manual header row in the wizard.

---

## Performance Rules

1. Sample data is computed from **at most the first 10 data rows** after header resolution.
2. The full Excel grid is **not** sent to the UI for mapping preview.
3. Raw preview remains stored server-side in `batch.raw_preview_json` for analyze/apply.

---

## Source Adapter Compatibility

All future adapters (CSV, XML, API, scraper, ERP) must implement the same `mapping_columns` shape in their preview response. The Excel adapter is the reference implementation (`build_mapping_preview_columns` in `column_mapper.py`).

---

## Implementation References

| Layer | Location |
|-------|----------|
| Sample builder | `backend/app/modules/imports/application/column_mapper.py` |
| Preview API | `GET /api/v1/data-integration/imports/{batch_id}/mapping-preview` |
| Wizard UI | `frontend/src/pages/ImportWizardPage.tsx` |
| Preview component | `frontend/src/components/imports/MappingFieldPreview.tsx` |

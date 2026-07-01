# Import Engine — Architecture

Import Engine is **source-agnostic**. v1 implements Excel only; PDF, scraper, and database connectors are planned as separate adapters that plug into the same core pipeline.

## Pipeline

```text
Import Source
    ↓
Extract Rows          ← source adapter (Excel, PDF, Scraper, Database, …)
    ↓
Normalize Rows        ← canonical fields, empty → null
    ↓
Validate Rows         ← company_name required; optional fields validated when present
    ↓
Duplicate Detection   ← batch + CRM customer matching
    ↓
Import Preview        ← batch + row statuses
    ↓
Merge Decision        ← create_new | update_existing | skip
    ↓
Apply Import          ← persist customers/contacts
```

## Source types

| Value      | Status in v1   | Notes                                      |
|------------|----------------|--------------------------------------------|
| `excel`    | Implemented    | `.xlsx` upload via `ExcelImportSourceAdapter` |
| `pdf`      | Planned        | Text extraction + OCR modes (future sprint) |
| `scraper`  | Planned        | User-provided scraper output               |
| `database` | Planned        | External DB / API transfer                 |
| `manual`   | Reserved       | Manual row entry                           |
| `other`    | Reserved       | Catch-all                                  |

Enum: `ImportSourceType` in `domain/value_objects.py`.

## Adapter port

```python
class ImportSourceAdapter(Protocol):
    source_type: ImportSourceType
    def extract_rows(self, payload: bytes, *, file_name: str) -> list[dict[str, Any]]: ...
```

Adapters must return rows keyed by `CANONICAL_FIELDS` (see `domain/services/header_mapping.py`).

**v1 adapter:** `application/source_adapters/excel_source_adapter.py`

**Future adapters (not in v1):**

- `PdfImportSourceAdapter` — text-based PDF extraction and OCR-based scanned PDF extraction; both feed the same pipeline after extraction.
- `ScraperImportSourceAdapter` — JSON/CSV from user scrapers.
- `DatabaseImportSourceAdapter` — external sync payloads.

## Required and optional fields

**Required (v1):** `company_name` only.

**Optional:** `email`, `phone`, `mobile_phone`, `website`, `country`, `city`, `address`, `tax_number`, `contact_first_name`, `contact_last_name`, `contact_title`, `contact_department`, `contact_email`, `contact_phone`, `contact_mobile_phone`, `notes`, `fair_name`, `hall`, `stand`.

A row with only `company_name` is valid. Missing optional fields do not produce validation errors.

## Sparse row handling

- Rows with `company_name` are processed.
- Optional fields that are empty or whitespace-only normalize to `null`.
- Completely blank Excel rows are skipped during extraction.
- Missing phone/email/address does **not** invalidate a row.
- When `email` or `contact_email` is present, multi-email validation applies.
- When `website` is present, simple URL validation applies.

## Module layout

| Layer        | Responsibility                                      |
|--------------|-----------------------------------------------------|
| `domain/`    | Entities, value objects, ports, normalizer, validator, duplicate detection |
| `application/source_adapters/` | Source-specific extraction                 |
| `application/import_row_builder.py` | Shared normalize → validate → duplicate pipeline |
| `application/upload_import.py`    | Upload use case (adapter + row builder)  |
| `application/apply_import.py`     | Apply merge decisions                      |

## API

- `POST /api/v1/imports/customers/upload` — Excel upload (v1)
- `GET /api/v1/imports/{batch_id}` — batch summary (`source_type` in response)
- `GET /api/v1/imports/{batch_id}/rows` — preview rows
- `PATCH /api/v1/imports/{batch_id}/rows/{row_id}/decision` — merge decision
- `POST /api/v1/imports/{batch_id}/apply` — apply batch

## Future PDF import

PDF import will be a separate sprint. Two extraction modes are planned:

1. **Text-based** — native PDF text layers
2. **OCR-based** — scanned documents

Both modes produce the same row shape and connect to the shared pipeline:

```text
PDF Extracted Rows → Import Rows → Preview → Decision → Apply
```

No PDF parsing code exists in v1; the adapter port and pipeline are designed to accept it without changing normalize/validate/duplicate/apply logic.

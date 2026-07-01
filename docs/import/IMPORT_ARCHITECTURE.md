# Data Integration — Import Architecture

**Module:** Data Integration (`data_integration`)  
**Frontend label:** Veri Entegrasyonu  
**Route:** `/data-integration`  
**Status:** Architecture (Sprint 09.0) — design only; implementation follows in later sprints.

This document defines the **Universal Import Standard** pipeline for KYROX Fair CRM. It extends the existing Import Engine ([IMPORT_ENGINE.md](../IMPORT_ENGINE.md)) and Smart Import Wizard (Sprint 07) into a source-agnostic, preview-first integration platform.

---

## Design principles

1. **Import is not direct insert.** Every batch passes through analysis, mapping, matching, preview, and explicit user decisions before persistence.
2. **Preview-first.** Upload and file analysis never write CRM domain data.
3. **Fair context required.** Batch-level `fair_id` is mandatory (ADR-012). Hall/stand belong on `CustomerFairParticipation`.
4. **Background execution.** Apply runs as a background job with progress and a final report.
5. **English backend, Turkish frontend.** API/module/table names in English; user-facing labels in Turkish.

See also: [MERGE_RULES.md](MERGE_RULES.md), [MATCHING_RULES.md](MATCHING_RULES.md), [DECISIONS.md](../DECISIONS.md) ADR-016.

---

## End-to-end pipeline

```text
Batch Setup
    ↓
File Analysis
    ↓
Header Mode (Excel)
    ↓
Column Mapping
    ↓
Normalization
    ↓
Smart Matching
    ↓
Preview
    ↓
Decision (per row / bulk)
    ↓
Background Import (Apply)
    ↓
Final Report
```

### Stage summary

| Stage | Purpose | CRM writes? |
|-------|---------|-------------|
| **Batch Setup** | User selects source type, fair, file(s), and batch metadata | No |
| **File Analysis** | Parse file structure, detect sheets, infer row count, sample values | No |
| **Header Mode** | Excel-only: declare how column headers are determined | No |
| **Column Mapping** | Map source columns → canonical CRM fields | No |
| **Normalization** | Canonical field values, Turkish/legal suffix cleanup, email/phone normalization | No |
| **Smart Matching** | Match rows to existing customers and fair participations; confidence scores | No |
| **Preview** | Row-level status, merge diff, validation errors, suggested actions | No |
| **Decision** | User confirms create / update / skip / manual review per row or bulk | No (decisions stored on batch rows) |
| **Background Import** | Apply approved rows in a job queue; idempotent, resumable | **Yes** |
| **Final Report** | Summary counts, failures, skipped, links to batch detail | Read-only |

---

## Batch Setup

User creates an **Import Batch** with:

| Field | Required | Notes |
|-------|----------|-------|
| `fair_id` | Yes | Selected fair for entire batch (ADR-012) |
| `source_type` | Yes | See source priority in ADR-016 |
| `file` / payload | Yes (file sources) | Stored for replay and audit |
| `mapping_template_id` | No | Reuse saved column mapping |
| `notes` | No | Operator context |

**Entry points:**

- **Veri Entegrasyonu → Import İşleri → Yeni Import**
- **Fuar Detayı → Katılımcıları İçe Aktar** (fair pre-filled; legacy `/imports` path migrates to `/data-integration` in implementation sprint)

---

## File Analysis

Source adapters extract **raw rows** without CRM semantics.

| Source | Adapter responsibility |
|--------|------------------------|
| Excel | Sheet selection, row/column bounds, typed cell reads |
| Web Scraper | Normalized scraper output → tabular rows |
| CSV | Delimiter/encoding detection |
| XML / JSON | Schema path → flat row projection |
| REST API | Paginated fetch → row stream |
| ERP | Connector-specific extract (future) |

Output: **raw row matrix** + metadata (sheet name, row numbers, sample values per column).

---

## Header Mode (Excel — mandatory)

On batch setup, user must choose **Excel Header Mode**:

| Mode | Turkish UI label | Behavior |
|------|------------------|----------|
| `first_row_header` | İlk satır başlık | Row 1 = column names; data from row 2 |
| `no_header` | Başlık yok | Columns labeled **A, B, C, D, …**; mapping uses sample values |
| `manual_header_row` | Başlık satırını ben seçeceğim | User picks header row index; rows above ignored |

### No-header mapping UX

When **Başlık yok** is selected:

- Mapping screen shows columns as **A, B, C, D, …**
- Each column displays **sample values** from the first N data rows (e.g. 3–5 examples)
- User manually maps A/B/C… → canonical fields (`company_name`, `email`, `phone`, …)
- `company_name` mapping is **required** before analysis can proceed

When **Başlık satırını ben seçeceğim** is selected:

- User selects row number (1-based UI)
- That row becomes header labels for mapping (same as first-row mode after selection)

---

## Column Mapping

Maps source columns → **canonical import fields**.

| Rule | Detail |
|------|--------|
| Required field | `company_name` only (single required mapping) |
| Optional fields | email, phone, website, country, city, hall, stand, contact fields, … |
| Template save | Mapping can be saved as **Mapping Şablonu** for reuse |
| No `fair_name` | Fair comes from batch `fair_id` only (ADR-012) |

Canonical field list aligns with `CANONICAL_FIELDS` in the Import Engine domain.

---

## Normalization

Applied after mapping, before matching:

- Trim whitespace; empty strings → `null`
- Company name normalization (see [MATCHING_RULES.md](MATCHING_RULES.md))
- Email: lowercase, multi-email split/merge rules
- Phone: E.164 or national format normalization (future sprint aligns with Customer Phones)
- Website: scheme normalization
- Turkish character folding for match keys (matching only; display preserves original where appropriate)

---

## Smart Matching

Two-level matching (ADR-012):

1. **Customer match** — existing `Customer` in organization
2. **Fair participation match** — existing `CustomerFairParticipation` for batch `fair_id`

Produces per row:

- `match_status` (new, duplicate, update_candidate, conflict, invalid, …)
- `confidence_score` (see [MATCHING_RULES.md](MATCHING_RULES.md))
- `suggested_action` (create_new, update_existing, skip, manual_review)
- `merge_preview` (field-level diff for updates)

---

## Preview

Preview screen shows:

- Row list with filters (all, new, update, duplicate, error, skip)
- **Merge diff viewer** (CRM vs import per field) — Sprint 07.1 baseline
- Bulk actions on filtered sets
- Validation errors inline
- No apply button without explicit user confirmation on decisions

---

## Decision

User sets row-level or bulk decisions:

| Decision | Meaning |
|----------|---------|
| `create_new` | New customer (+ participation if fair batch) |
| `update_existing` | Merge into matched customer/participation per merge rules |
| `skip` | Row ignored on apply |
| `manual_review` | Held for operator; not applied until resolved |

Decisions are persisted on `ImportRow` before apply. Default: conservative (no overwrite of populated CRM fields).

---

## Background Import (Apply)

Apply runs as a **background job**:

- Job record with status: `queued` → `running` → `completed` | `failed` | `partial`
- Progress: processed / total rows
- Row-level apply results stored for audit
- Idempotent re-run rules (same batch + same decisions)
- Core audit events for applied changes (via KYROX Core integration)

User can navigate away; **Import Geçmişi** shows job status.

---

## Final Report

After job completion:

| Metric | Description |
|--------|-------------|
| Created customers | Count |
| Updated customers | Count |
| Participations created/updated | Count |
| Contacts added | Count |
| Skipped | Count |
| Failed | Count with error detail |
| Manual review remaining | Count |

Report is downloadable and linked from batch detail. Failures do not roll back successful rows unless batch policy specifies transactional apply (default: **continue on row error**, collect failures).

---

## Frontend navigation (Veri Entegrasyonu)

**Route:** `/data-integration`

| Menu item | Route (planned) | Status |
|-----------|-----------------|--------|
| Import İşleri | `/data-integration/imports` | Active (Sprint 07 wizard migrates here) |
| Import Geçmişi | `/data-integration/history` | Planned |
| Mapping Şablonları | `/data-integration/templates` | Planned |
| Web Scrapers | — | 🚧 Disabled |
| Export İşleri | — | 🚧 Disabled |
| API Entegrasyonları | — | 🚧 Disabled |
| ERP Entegrasyonları | — | 🚧 Disabled |
| CSV/XML Kaynakları | — | 🚧 Disabled |
| Senkronizasyon İşleri | — | 🚧 Disabled |
| Entegrasyon Ayarları | — | 🚧 Disabled |

Disabled items are visible in navigation with 🚧 badge; clicking shows “Yakında” placeholder.

---

## Relationship to existing code

| Artifact | Sprint | Evolution in 09.x |
|----------|--------|-------------------|
| Import Engine pipeline | 07 | Adapters + normalization + matching formalized |
| Smart Import Wizard UI | 07–07.1 | Moves under Veri Entegrasyonu |
| `POST /api/v1/imports/*` | 07 | Evolves toward `/api/v1/data-integration/*` (implementation sprint) |
| Legacy `/imports` route | 07 | Deprecated; redirect to `/data-integration` |

Sprint 09.0 delivers **documentation and ADR-016 only**. No API or UI code changes in this sprint.

---

## Background job standard

Import apply, future export, and sync jobs share:

- Job entity with organization scope
- Status enum + progress counters
- Error aggregation
- List/detail API for **Import Geçmişi**
- Frontend polling or SSE for progress (implementation choice in Phase 2)

---

## Permissions (sketch)

| Permission | Scope |
|------------|-------|
| `data_integration:read` | List batches, history, templates |
| `data_integration:import` | Create batch, upload, map, preview, decide |
| `data_integration:apply` | Trigger background apply |
| `data_integration:admin` | Templates, integration settings (future) |

Exact permission strings finalized in implementation sprint with KYROX Core registration.

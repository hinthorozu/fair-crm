# Smart Import Wizard — Functional Specification

**Status:** Design (Functional Design Phase — Sprint 07 Smart Import Wizard)  
**Scope:** `fair-crm` product only  
**Implementation:** Forbidden until this document and companion UX / merge docs are approved  
**Builds on:** Import Engine v1 ([IMPORT_ENGINE.md](IMPORT_ENGINE.md)), ADR-005, ADR-010, ADR-012

---

## 1. Purpose

Smart Import Wizard is a **decision-support data transfer system**, not a file upload screen. It lets users safely bring company data from heterogeneous sources into FAIR CRM with preview, validation, duplicate review, and explicit merge decisions before any CRM record changes.

**First implementation target:** Excel (`.xlsx`).  
**Architecture target:** Source-agnostic pipeline reusable for PDF, scraper output, external database, manual entry, and other sources.

---

## 2. Product Vision

| Principle | Requirement |
|-----------|-------------|
| No blind insert | CRM writes only after user review and apply (ADR-005) |
| Sparse data tolerance | Only `company_name` is guaranteed; all other fields optional |
| Multi-entity outcome | Import may create/update Customer, Contact, CustomerFairParticipation, Activity |
| Fair context required | User selects Fair before mapping; batch carries `fair_id`; hall/stand → `CustomerFairParticipation`, never on Customer or Fair (ADR-010, ADR-012) |
| Source extensibility | New sources plug in via `ImportSourceAdapter`; shared normalize → validate → duplicate → apply pipeline |
| Turkish UI | Frontend labels and messages in Turkish; API/schema in English |

---

## 3. Domain Model Context

```text
Customer
    │
    ├── Contacts
    ├── Activities
    │
    └──── CustomerFairParticipation ─── Fair
              hall, stand, participation_status, notes, …
```

Import **must not** be modeled as “Customer-only insert.” Each analyzed row may produce zero or more planned operations:

| Entity | When created/updated |
|--------|----------------------|
| **Customer** | Always the primary anchor when row is valid and decision ≠ skip |
| **CustomerFairParticipation** | Always for the batch-selected Fair when row decision ≠ skip (ADR-012) |
| **Contact** | When contact fields present; match by customer + name or create new |
| **Activity** | Optional post-apply audit note (v1 behavior); extended fair-scoped activity in later phase |

---

## 4. Relationship to Import Engine v1

v1 already provides:

- `ImportBatch` / `ImportRow` persistence
- Excel adapter with **automatic** Turkish header alias mapping
- Normalize → validate → duplicate → decision → apply pipeline
- Single-page `/imports` UI (upload → preview → decisions → apply)

Smart Import Wizard **evolves** v1 by adding:

1. **Explicit wizard steps** (9 screens) instead of one combined page
2. **Manual column mapping** with header/no-header and column-letter support
3. **Source selection** screen (Excel active; others disabled with “Yakında”)
4. **Richer preview** (confidence score, bulk decisions, participation preview)
5. **Participation-aware apply** (hall/stand on join entity)
6. **Batch lifecycle** suitable for large files and future background processing

v1 automatic header mapping remains available as **“Otomatik eşleştirme öner”** on Screen 4 (Column Mapping); user can override every mapping.

---

## 5. Canonical Import Fields

Aligned with `CANONICAL_FIELDS` in the import module.

### 5.1 Required

| Canonical key | Description |
|---------------|-------------|
| `company_name` | Company / customer display name — **only required field** |

### 5.2 Optional — Customer

| Canonical key | Description |
|---------------|-------------|
| `email` | Customer email(s); multi-email supported |
| `phone` | Primary phone |
| `mobile_phone` | Mobile phone |
| `website` | URL |
| `country` | Country |
| `city` | City |
| `address` | Address |
| `tax_number` | Tax / registration number |

**Note:** Mapped field `notes` is stored on **CustomerFairParticipation.notes** (participation scope, ADR-012), not on Customer.

### 5.3 Optional — Contact

| Canonical key | Description |
|---------------|-------------|
| `contact_first_name` | Contact first name |
| `contact_last_name` | Contact last name |
| `contact_title` | Job title |
| `contact_department` | Department |
| `contact_email` | Contact email(s) |
| `contact_phone` | Contact phone |
| `contact_mobile_phone` | Contact mobile |

### 5.4 Optional — Fair participation (ADR-010, ADR-012)

| Canonical key | Maps to | Notes |
|---------------|---------|-------|
| `hall` | `CustomerFairParticipation.hall` | Not on Customer or Fair |
| `stand` | `CustomerFairParticipation.stand` | Not on Customer or Fair |
| `notes` | `CustomerFairParticipation.notes` | Participation-scoped free text |

**Fair context (batch-level, ADR-012):** User selects the target Fair on Screen 3 (Fair Selection). The batch carries `fair_id`; all rows in the batch are imported into that Fair's participation context. **`fair_name` is not a supported mapping field** — import sources (Excel, PDF, scraper, etc.) will not provide or resolve fair names.

**Alternative entry:** When import is launched from Fair Detail → Katılımcı Firmalar → Katılımcıları İçe Aktar, the Fair is pre-selected and Screen 3 is skipped or read-only.

### 5.5 Future canonical fields (design-ready, not v1 wizard)

| Canonical key | Purpose |
|---------------|---------|
| `participation_status` | Override default `exhibitor` on participation |
| `participation_notes` | Participation-scoped notes |
| `visited_at` | Fair visit timestamp |

---

## 6. Source Types

Enum: `ImportSourceType` (existing).

| Source | Wizard Screen 1 | v1 Wizard impl | Adapter responsibility |
|--------|-----------------|----------------|----------------------|
| `excel` | Active | Yes | Parse `.xlsx`; return raw grid + metadata |
| `pdf` | Disabled | No | Extract text/OCR → tabular rows |
| `scraper` | Disabled | No | Parse JSON/CSV scraper export |
| `database` | Disabled | No | Map external DB query result |
| `manual` | Disabled | No | Empty grid or pasted rows |
| `other` | Disabled | No | Generic structured upload |

Each adapter returns **raw rows** (Screen 2 output shape):

```json
{
  "source_type": "excel",
  "file_name": "exhibitors.xlsx",
  "sheet_name": "Sheet1",
  "has_header_row": null,
  "columns": [
    { "index": 0, "letter": "A", "header_label": null, "sample_values": ["ABC", "DEF"] },
    { "index": 1, "letter": "B", "header_label": null, "sample_values": ["info@a.com", ""] }
  ],
  "rows": [
    { "row_index": 1, "cells": { "0": "ABC Ltd", "1": "info@a.com" } }
  ]
}
```

No normalization, validation, duplicate detection, or CRM writes at upload time.

---

## 7. Wizard Screens — Functional Requirements

Wizard flow (9 steps):

```text
1. Import Source seç
2. Dosya yükle
3. Fuar seç
4. Kolon eşleştir
5. Analiz et
6. Önizleme / duplicate review
7. Merge kararları
8. Apply
9. Summary
```

---

### Screen 1 — Import Source

**Goal:** Choose data origin.

**Inputs:**

- Source type (radio/card list)
- Optional: **Import label** (batch display name, default = file name or timestamp)

**Outputs:**

- `batch_id` created in `draft` state (or session) with `source_type`, `status = source_selected`
- Navigation to Screen 2

**Rules:**

- Only `excel` selectable in v1; others show tooltip “Yakında”
- No file required yet
- No Fair selection on this screen (Screen 3)
- No CRM side effects

---

### Screen 2 — Upload

**Goal:** Ingest raw source payload.

**Inputs:**

- File picker (Excel: `.xlsx` only in v1)
- Future: connection config, paste area, API credentials

**Processing:**

- Adapter `extract_raw_preview()` — **new port method** (design); distinct from v1 `extract_rows()` which applies header mapping
- Store raw grid in batch storage (DB JSON or object storage — implementation TBD)
- Compute column letters (A, B, …), sample values (first N non-empty per column), optional detected header candidates

**Explicit non-goals at this stage:**

- No Customer / Contact / Activity / Participation creation
- No duplicate detection
- No validation
- No automatic header mapping applied to canonical fields

**Outputs:**

- Raw preview API response for Screen 3 (Fair Selection) or Screen 4 (Column Mapping) if Fair pre-selected
- Batch status → `uploaded`

**Edge cases:**

| Case | Behavior |
|------|----------|
| Empty file | Error: “Dosya boş veya okunamadı” |
| Multiple sheets | Sheet selector (default: first sheet) |
| > N rows (e.g. 10,000) | Warn; allow continue; flag batch for background analyze (see §12) |
| Password-protected Excel | Error with clear message |
| Wrong extension | Block before upload |

---

### Screen 3 — Fair Selection

**Goal:** Select the target Fair for the entire import batch (ADR-012).

**Inputs:**

- **Fair** dropdown (required) — active fairs only, sorted by date descending
- Pre-filled when user enters via Fair Detail → Katılımcı Firmalar → Katılımcıları İçe Aktar (`fair_id` in route/query context)

**Display for selected Fair:**

| Field | Example |
|-------|---------|
| Fuar adı | WIN Eurasia 2026 |
| Tarih aralığı | 5–8 Haziran 2026 |
| Lokasyon | İstanbul Fuar Merkezi |
| Mevcut katılımcı sayısı | 1.842 |

**Validation before continue:**

- Fair **must** be selected — hard gate
- Selected Fair must be active (not archived)

**Outputs:**

- `fair_id` persisted on batch
- Batch status → `fair_selected`
- Navigation to Screen 4

**Rules:**

- One Fair per batch; applies to all rows
- No `fair_name` lookup from source data
- No CRM side effects (read-only Fair list)

**Alternative entry (Fair pre-selected):**

```text
Fuarlar → Fuar Detayı → Katılımcı Firmalar → Katılımcıları İçe Aktar
```

When launched from this path, Fair is already in context; Screen 3 shows read-only Fair summary with option to change (returns to dropdown) or proceeds directly.

---

### Screen 4 — Column Mapping

**Goal:** User maps each CRM canonical field to a source column (or none).

**Critical UX inputs:**

1. **“İlk satır başlık mı?”** — Yes / No / Otomatik (default: Otomatik with explanation)
2. Per-field mapping control:
   - CRM field (Turkish label) → Source column dropdown
   - Options: `Column A`, `Column B`, … and if header mode: `Firma Adı`, `Telefon`, …
   - “Eşleştirme yok” for optional fields
3. **“Otomatik eşleştirme öner”** button — runs v1 `header_mapping` heuristics + Turkish aliases; user confirms/overrides
4. Live preview table: first 5 mapped rows

**Supported mapping fields (ADR-012):** `company_name` (required), `email`, `phone`, `mobile_phone`, `website`, `country`, `city`, `address`, `tax_number`, `contact_first_name`, `contact_last_name`, `contact_title`, `contact_department`, `contact_email`, `contact_phone`, `contact_mobile_phone`, `notes`, `hall`, `stand`. **`fair_name` is not supported** and must not appear in the mapping UI or auto-suggest heuristics.

**Validation before continue:**

- `company_name` **must** be mapped — only hard gate
- Warn (non-blocking) if duplicate mappings (two CRM fields → same column)
- Warn if mapped email column looks numeric-only

**Outputs:**

- Persisted `column_mapping_json` on batch:
  ```json
  {
    "has_header_row": true,
    "mappings": {
      "company_name": { "type": "column_index", "value": 1 },
      "email": { "type": "column_header", "value": "E-posta" }
    }
  }
  ```
- Batch status → `mapped`

**Headerless Excel support:**

- When `has_header_row = false`, row 1 is data; mapping uses column index/letter only
- UI shows letters prominently: “Kolon B → Firma Adı”

---

### Screen 5 — Analyze

**Goal:** Run pipeline without CRM mutation.

**Pipeline (batch job or synchronous for small files):**

```text
Apply column mapping → Extract canonical raw rows
    ↓
Normalize (company name, email, phone, …)
    ↓
Validate (company_name required; conditional rules on present fields)
    ↓
Duplicate detection — two levels (see §11):
    ↓
Merge suggestions (default decision per row, customer + participation aware)
    ↓
Participation preview (batch `fair_id`, hall/stand attachment plan)
    ↓
Persist ImportRow records with full analysis payload
```

**Outputs per row:**

- `row_status`: `new` | `update_candidate` | `duplicate` | `invalid`
- `normalized_data_json`
- `validation_errors[]`
- `duplicate_match`: `{ customer_id, match_type, confidence_score }` or null
- `participation_match`: `{ participation_id, exists_in_fair: bool }` or null
- `suggested_decision`: `create_new` | `update_existing` | `skip`
- `suggested_actions`: composite hint — e.g. `create_customer_and_participation`, `existing_customer_create_participation`, `existing_customer_update_participation`, `existing_customer_skip_participation`
- `participation_plan`: `{ fair_id, hall, stand, action: create|update|skip }` — `fair_id` always from batch

**Batch status:** `analyzed`

**User feedback:**

- Progress indicator for large batches
- Summary counts: total, valid, invalid, duplicates, new

**Non-goals:** No CRM writes.

---

### Screen 6 — Import Preview / Duplicate Review

**Goal:** Row-level review before decisions finalized.

**Table columns (Turkish labels):**

| Column | Source |
|--------|--------|
| Firma | `company_name` normalized |
| E-posta | `email` |
| Telefon | `phone` |
| Web | `website` |
| Ülke / Şehir | `country`, `city` |
| Salon / Stand | participation plan preview (batch Fair shown in page header) |
| Eşleşen müşteri | matched customer name + link (if customer duplicate) |
| Katılım durumu | Yeni katılım / Mevcut katılım / — |
| Güven skoru | `confidence_score` 0–100% |
| Durum | badge: Yeni / Güncellenecek / Duplicate / Hatalı |
| Karar | current decision (editable on Screen 7) |
| Hatalar | validation error summary |

**Filters:**

- Durum (all / new / update / duplicate / invalid)
- Karar (all / create / update / skip / unset)
- Search by company name

**Row expansion (optional):** Show normalized JSON, raw source cells, duplicate match detail.

**Batch status:** `preview_ready`

---

### Screen 7 — Merge Decision

**Goal:** User confirms or overrides per-row and bulk decisions.

**Per-row actions:**

- **Oluştur** (`create_new`)
- **Güncelle** (`update_existing`) — enabled only when duplicate match exists
- **Atla** (`skip`)

**Bulk actions (with confirm dialog):**

| Action | Effect |
|--------|--------|
| Tüm yenileri oluştur | All `new` rows → create |
| Tüm eşleşenleri güncelle | All `duplicate`/`update_candidate` with match → update |
| Tüm duplicate kayıtları atla | All duplicate rows → skip |
| Tüm hatalı kayıtları atla | All `invalid` → skip |
| Kararları sıfırla | Revert to `suggested_decision` |

**Rules:**

- Invalid rows cannot be set to create/update unless user fixes data (future: inline edit) — v1: skip only
- Update without match → blocked
- Changing decision updates `ImportRow.decision` only; still no CRM write

**Batch status:** `decisions_set`

---

### Screen 8 — Apply

**Goal:** Execute CRM updates inside a transaction per row (or batched transaction — implementation detail).

**Apply order per row (when not skipped):**

```text
batch fair_id
    ↓
Customer find/create (per merge rules)
    ↓
CustomerFairParticipation find/create/update (always for batch Fair)
    ↓
hall / stand written on participation only (never on Customer or Fair)
    ↓
Contact find/create/update
    ↓
Activity (source = import)
```

1. **Customer** — create or update per merge rules ([IMPORT_WIZARD_MERGE_RULES.md](IMPORT_WIZARD_MERGE_RULES.md))
2. **CustomerFairParticipation** — always for batch `fair_id`; create or update per participation merge rules
3. **Contact** — create or patch empty fields on matched contact
4. **Activity** — import note (`source = import`, `type = note`)

**UI:**

- Summary of pending operations: X create, Y update, Z skip
- Confirm dialog: “X müşteri oluşturulacak, Y güncellenecek. Devam?”
- Progress bar during apply
- Partial failure handling: continue or stop on first error (design: **continue**, collect failures)

**Batch status:** `applying` → `completed` | `completed_with_errors` | `failed`

---

### Screen 9 — Summary

**Goal:** Batch report and next actions.

**Metrics:**

| Metric | Description |
|--------|-------------|
| Oluşturulan | Customers created |
| Güncellenen | Customers updated |
| Katılım eklenen/güncellenen | Participations created/updated |
| Kişi eklenen/güncellenen | Contacts created/updated |
| Atlanan | Rows skipped |
| Başarısız | Rows failed with error detail |

**Additional UI:**

- Download error report (CSV of failed rows)
- Link to affected customers (where created/updated)
- “Yeni içe aktarma” CTA
- Batch list entry with timestamp, source, user

**Batch status:** terminal (`completed`, `completed_with_errors`, `failed`, `cancelled`)

---

## 8. Batch Lifecycle & States

```text
draft → source_selected → uploaded → fair_selected → mapped → analyzing → analyzed
    → preview_ready → decisions_set → applying → completed | completed_with_errors | failed
```

| State | User can |
|-------|----------|
| `draft` … `fair_selected` | Change Fair, re-upload |
| `mapped` | Edit mapping, re-upload, change Fair |
| `analyzed` … `decisions_set` | Re-run analyze if mapping or Fair changed |
| `applying` | Wait (read-only) |
| `completed*` | View summary only |

**Cancel:** Allowed before `applying`; soft-delete batch or mark `cancelled`.

---

## 9. API Design (Future — Not Implemented in Design Phase)

Conceptual endpoints extending v1:

| Method | Path | Screen |
|--------|------|--------|
| POST | `/imports/batches` | 1 — create batch |
| PATCH | `/imports/batches/{id}/source` | 1 |
| POST | `/imports/batches/{id}/upload` | 2 |
| GET | `/imports/batches/{id}/raw-preview` | 3–4 |
| PUT | `/imports/batches/{id}/fair` | 3 — set `fair_id` |
| PUT | `/imports/batches/{id}/mapping` | 4 |
| POST | `/imports/batches/{id}/analyze` | 5 |
| GET | `/imports/batches/{id}/rows` | 6–7 |
| PATCH | `/imports/batches/{id}/rows/{row_id}/decision` | 7 |
| POST | `/imports/batches/{id}/decisions/bulk` | 7 |
| POST | `/imports/batches/{id}/apply` | 8 |
| GET | `/imports/batches/{id}/summary` | 9 |

v1 paths remain for backward compatibility until migration window closes.

---

## 10. Fair Context Rules (ADR-012)

Every import batch **must** carry a `fair_id` set on Screen 3 (Fair Selection) or pre-filled from Fair Detail entry.

| Rule | Behavior |
|------|----------|
| Fair source | User dropdown or pre-selected context — never from import file |
| Batch scope | Single `fair_id` applies to all rows in the batch |
| Participation | Every non-skipped row creates or updates `CustomerFairParticipation` for batch `fair_id` |
| Hall / Stand | Written only on `CustomerFairParticipation` — **never** on Customer or Fair (ADR-010) |
| Archived Fair | Block Fair selection on Screen 3; batches with archived Fair cannot proceed to analyze |

No `fair_name` resolution, lookup, or auto-create from source data.

---

## 11. Duplicate Detection (Functional)

Duplicate detection operates at **two levels** (ADR-012). Both levels inform the suggested decision and participation plan.

### 11.1 Level 1 — Customer duplicate

Does the same or similar company already exist in CRM?

| Match type | Confidence | Notes |
|------------|------------|-------|
| Exact normalized name | 100% | Strong customer match |
| Fuzzy name (SequenceMatcher ≥ threshold) | 70–99% | Review recommended |
| Email exact match on customer | 95% | Strong customer match |
| In-batch duplicate (second occurrence) | — | Second row → skip by default |

### 11.2 Level 2 — Participation duplicate

Within the **batch-selected Fair**, does the matched (or to-be-created) Customer already have a participation record?

| Customer in CRM | Participation in selected Fair | Suggested action |
|-----------------|-------------------------------|------------------|
| No | — | Create Customer + Create Participation |
| Yes | No | Existing Customer + Create Participation |
| Yes | Yes | Existing Customer + Update Participation / Skip |

**Examples:**

```text
ABC Makina CRM'de var. Seçilen fuarda yok.
→ Action: Existing Customer + Create Participation

ABC Makina CRM'de var. Seçilen fuarda da var.
→ Action: Existing Customer + Update Participation / Skip

ABC Makina CRM'de yok.
→ Action: Create Customer + Create Participation
```

**Confidence score** reflects primarily Customer match strength; participation status shown separately on Screen 6. User always overrides on Screen 7.

---

## 12. Performance & Background Processing

| Threshold | Behavior |
|-----------|----------|
| ≤ 500 rows | Synchronous analyze + apply |
| > 500 rows | Async job; email/in-app notification when analyze complete (future) |
| > 10,000 rows | Require confirmation; recommend split file |

Design prepares `batch.job_id` and status polling; v1 wizard may implement synchronous only with warning banner.

---

## 13. Security & Tenancy

- All batch operations scoped by `organization_id` from auth context
- Uploaded files stored org-scoped; retention policy TBD (default: 30 days after complete)
- No PII in application logs; row content in audit via Core audit API on apply

---

## 14. Activity Generation (Import Audit)

**v1 wizard (minimum):**

- On customer create/update: Activity `type=note`, `source=import`, subject “İçe aktarma”, description includes batch id and row summary

**Future:**

- Fair-scoped activity linked via `participation_id` (ADR-011)
- User toggle on Screen 1: “İçe aktarma aktivitesi oluştur” (default: on)

---

## 15. Edge Cases Catalog

| # | Scenario | Expected behavior |
|---|----------|-------------------|
| E1 | Row with only company name | Valid; create customer with null optional fields |
| E2 | Headerless 3-column file | User maps B→company_name via letter |
| E3 | Same company twice in file | Second row flagged in-batch duplicate |
| E4 | Update decision but CRM customer archived | Apply fails row; error “Müşteri arşivlenmiş” |
| E5 | Customer exists but not in selected Fair | Create/update Customer; create new participation for batch Fair |
| E6 | Customer and participation both exist in selected Fair | Update participation per merge rules; user may skip |
| E7 | Multi-email in one cell | Normalize to `;` separated canonical form |
| E8 | User changes mapping after analyze | Require re-analyze; clear prior decisions |
| E9 | User changes Fair after analyze | Require re-analyze; clear prior decisions |
| E10 | Apply interrupted (network) | Batch `completed_with_errors`; idempotent row apply via row status |
| E11 | Empty company_name after mapping | Row invalid; cannot create |
| E12 | PDF source selected (future) | Disabled in v1 |
| E13 | Import from Fair Detail with pre-selected Fair | Screen 3 read-only or skipped; `fair_id` set on batch create |

---

## 16. Success Criteria (for Implementation Phase)

- [ ] 9-screen wizard navigable with back/next guards per batch state
- [ ] Mandatory Fair selection (Screen 3) with batch `fair_id`
- [ ] Fair Detail entry path pre-fills Fair context
- [ ] Manual column mapping without `fair_name` field
- [ ] Two-level duplicate detection (Customer + Participation)
- [ ] Analyze produces preview without CRM writes
- [ ] Bulk + per-row decisions
- [ ] Apply creates/updates participation for batch Fair with hall/stand on join entity only
- [ ] Summary report with created/updated/skipped/failed counts
- [ ] Excel-only source active; others visible but disabled
- [ ] Turkish UI throughout
- [ ] Backend tests for Fair context, mapping, analyze, apply participation path

---

## 17. References

- [IMPORT_ENGINE.md](IMPORT_ENGINE.md)
- [IMPORT_WIZARD_UX_FLOW.md](IMPORT_WIZARD_UX_FLOW.md)
- [IMPORT_WIZARD_MERGE_RULES.md](IMPORT_WIZARD_MERGE_RULES.md)
- [DECISIONS.md](DECISIONS.md) — ADR-005, ADR-010, ADR-011, ADR-012
- [PROJECT_CONSTITUTION.md](../PROJECT_CONSTITUTION.md)

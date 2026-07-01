# fuar-crm Reference Analysis

**Status:** Sprint 1.0.0 Phase 1 — completed  
**Source:** `fuar-crm` repository (reference-only per ADR-004)  
**Target:** `fair-crm` on KYROX Core  
**Rule:** Extract business concepts only — do not copy architecture, auth, permissions, or code.

---

## 1. Legacy repository snapshot

| Item | Value |
|------|-------|
| Location | `KYROX/fuar-crm` (sibling to fair-crm) |
| Version | ~v0.1.9–v0.2.3 |
| Stack | FastAPI monolith, SQLAlchemy, MySQL/MariaDB |
| Implemented CRM APIs | Customers, contacts, phones, emails, fairs, participations, notes, dashboard |
| Import/scraper APIs | **Not implemented** — schema, seed samples, and docs only |
| Auth | Local JWT + embedded org/RBAC (→ **KYROX Core** in fair-crm) |

---

## 2. Customer fields (legacy → fair-crm mapping)

Legacy aggregate is `Customer` with primary label **`company_name`** (not a separate legal/trade split).

| Legacy field | fair-crm equivalent | Reuse? |
|--------------|---------------------|--------|
| `company_name` | `display_name` | **Yes** — primary UI label |
| — | `legal_name`, `trade_name` | Optional split (not in legacy) |
| `normalized_company_name` | `normalized_name` | **Yes** — duplicate matching |
| `website` + `normalized_website` | `website` (+ computed normalized in app) | **Yes** |
| `main_phone` + `normalized_main_phone` | `phone` | **Yes** — single primary phone on Customer for Sprint 1 |
| `tax_number`, `tax_office` | same | **Yes** |
| `country`, `city` | same | **Yes** |
| `district` | — | **Consider adding** — used in legacy search/address |
| `address` | — | **Consider adding** (TEXT) — legacy search includes address |
| `description` | — | **Consider adding** (TEXT) — free-form CRM notes at account level |
| `source` | `source` | **Yes** — values: `manual`, `seed`, `excel`, `scraper` |
| `is_active` | `status` enum | **Map conceptually** — legacy boolean → fair-crm `lead/active/inactive/archived` |
| `is_deleted` + `deleted_at` | `deleted_at` + `status=archived` | **Yes** — soft delete pattern |
| — | `customer_type` | **New in fair-crm** — legacy has no exhibitor/lead/supplier typing |

### Related child entities (legacy — later sprints)

Legacy stores **multiple phones and emails** in `customer_phones` / `customer_emails` with:

- `phone_type` / `email_type`, `label`, `is_primary`, `source`
- Email `validation_status` (`unknown`, …), `validation_message`
- Optional link to `contact_id`

**Conceptual reuse:** Sprint 1 keeps one phone/email on Customer; Sprint 1.1+ Contact module should align with legacy’s richer channel model.

---

## 3. Normalization & duplicate detection (high value)

Legacy `app/utils/normalization.py` defines production-tested rules:

### Company name

1. Turkish character fold (ç→c, ğ→g, ı/İ→i, …)
2. NFKD accent strip
3. Uppercase ASCII
4. Remove non-alphanumeric (keep spaces)
5. Collapse whitespace
6. Strip legal suffixes (regex list): `ANONIM SIRKETI`, `A.S.`, `AS`, `LTD STI`, `LIMITED`, `SANAYI`, `TICARET`, `VE`, …

**Reuse in fair-crm:** Align Sprint 1 `customer_name_normalizer` with this suffix list (fair-crm design is close; merge legacy patterns).

### Phone

- Digits only; normalize Turkish numbers to `90` + 10 digits (handles `0`, `90`, 10-digit forms).

**Reuse:** Port phone normalization logic conceptually for import matching (Sprint 1.4+).

### Email / website

- Email: trim, lowercase
- Website: strip `http(s)://`, `www.`, path — domain only

**Reuse:** Same rules for import duplicate detection on website/email keys.

### Duplicate detection (designed, partially seeded)

Legacy **does not implement** matching algorithms in API code. Design + seed data define:

| Concept | Legacy values |
|---------|----------------|
| `detection_status` | `new`, `possible_duplicate` |
| `decision_status` | `pending` (awaiting user: merge / skip / create) |
| `match_score` | Decimal 0–100 (e.g. 86.25–94.50 in seed) |
| `detected_customer_id` | Link to existing customer |
| `warning_message` | Turkish operator hint (UI text) |

**Business rules (docs + seed):**

- Never blind insert from import
- Never auto-overwrite existing customer data
- User must choose merge / skip / create
- Prefer merge when duplicate confirmed
- Scraper output must go through Import Engine, not direct CRM writes

**Reuse in fair-crm:** Matches ADR-005 and Sprint 1.4 design — implement scoring and statuses as documented here.

---

## 4. Import / Excel behavior (conceptual — no API yet)

### Data model (reuse structurally in Sprint 1.4)

**ImportBatch**

| Field | Purpose |
|-------|---------|
| `fair_id` | Optional fair context for exhibitor list |
| `source_type` | `excel`, `scraper` |
| `source_name`, `original_file_name` | Traceability |
| `status` | e.g. `uploaded`, `preview_ready` |
| `total_rows`, `successful_rows`, `warning_rows`, `error_rows` | Batch stats |
| `created_by_user_id` | Actor |

**ImportRow**

| Field | Purpose |
|-------|---------|
| `row_number` | Excel row index |
| `raw_data_json` | Original row payload |
| `normalized_data_json` | Normalized fields for matching |
| `detected_customer_id`, `detected_fair_participation_id` | Match targets |
| `match_score`, `detection_status`, `decision_status` | Duplicate workflow |
| `decision_payload_json` | User merge/create choices |
| `warning_message`, `error_message` | Row-level feedback |

### Workflow (from docs + MASTER_CONTEXT)

```text
Excel upload → Import Batch → Import Rows (preview)
  → Validation → Normalization → Duplicate Detection
  → User decisions (merge/skip/create) → Commit to CRM
  → Audit log
```

### Excel row fields (from seed samples)

Typical exhibitor import columns:

- `company_name`, `phone`, `email`, `website`
- `hall`, `stand_number` (fair participation context)

**Reuse:** Import column mapping and preview row shape for Sprint 1.4.

---

## 5. Existing CRM workflows (implemented APIs)

| Workflow | Legacy behavior | fair-crm note |
|----------|-----------------|---------------|
| Create customer | Auto-compute normalized fields on create | Same on create/update |
| List/search | `search` across name, normalized name, country, city, address, website, phone | Reuse search scope; add API pagination (cursor) |
| Customer profile | `GET /customers/{id}/profile` — customer + contacts + phones + emails + participations + notes | Reuse as **read model** concept; split across modules/sprints |
| Update | Partial update + re-normalize | Same |
| Delete | Soft delete (`is_deleted`, `deleted_at`) | Map to archive + `deleted_at` |
| Dashboard | Counts + recent customers/fairs + pending import decisions | Product reporting sprint; use Core for audit |

### Fair participation (Sprint 1.3 reference)

- Unique `(customer_id, fair_id)`
- Fields: `hall`, `stand_number`, `exhibitor_profile_url`, `external_exhibitor_id`
- `participation_status` default `active`; `source` tracking

### Contact (Sprint 1.1 reference)

- `full_name`, `normalized_full_name`, `title`, `department`, `phone`, `email`, `is_primary`
- Optional `note` on contact

### Notes

- Linked to customer; optional contact, fair, participation
- `note_type` e.g. `follow_up`, `import_test`
- Turkish detail text in seed (frontend language rule)

---

## 6. Naming conventions worth preserving

| Area | Convention |
|------|------------|
| Backend / DB / API | English (`company_name` → fair-crm `display_name`, `fair_participations`, `import_batches`) |
| Frontend labels | Turkish (legacy seed messages, operator warnings) |
| Table prefix | Legacy: plain names; fair-crm: `crm_*` |
| Source tracking | `manual`, `excel`, `scraper`, `seed` on entities |
| API paths | kebab-case plural (`/fair-participations`) — fair-crm uses `/api/v1/...` |
| Normalized columns | Store both raw display and normalized for matching |

---

## 7. Business rules summary

1. **Import never writes CRM directly** — always batch → rows → preview → decisions.
2. **Duplicate detection** on normalized company name, phone, email, website (tax number noted as future).
3. **No automatic overwrite** on merge — user confirms.
4. **Prefer merge** over creating duplicate accounts.
5. **Scraper → Import Engine → CRM** — no scraper direct insert.
6. **Soft delete** for customers and related entities — no hard delete by default.
7. **Customer is the hub** — contacts, channels, participations, notes hang off customer.
8. **Fair participation** ties customer to fair with stand/hall metadata.
9. **Primary contact / primary phone / primary email** flags for UI defaults.
10. **Transactions** for import, merge, bulk operations (legacy DB guidelines).

---

## 8. Explicitly do NOT reuse from fuar-crm

| Area | Reason |
|------|--------|
| Monolithic FastAPI + embedded auth | fair-crm uses separate service + KYROX Core APIs |
| Local `Organization`, `User`, `Role`, `Permission` models | Core identity platform |
| Local `AuditLog` table/API | Core audit write/query APIs |
| MySQL-specific JSON TEXT adapter | fair-crm targets PostgreSQL |
| Integer PKs | fair-crm uses UUID |
| `company_name` API field name | fair-crm uses `display_name` per ADR-003 |
| Router/repository structure | fair-crm layered modules per Core standards |
| JWT in product service | Login via Core; product validates token only |

---

## 9. Recommended updates to fair-crm Sprint 1 design

Before Phase 2 implementation, consider these **conceptual** adjustments (no code in this step):

| Topic | Recommendation |
|-------|----------------|
| Customer fields | Add optional `district`, `address`, `description` if operators need parity with legacy search/profile |
| Normalization | Extend legal suffix list to match legacy `LEGAL_SUFFIX_PATTERNS` |
| Phone normalization | Document TR `90` prefix rule for future import matching |
| Search | Plan list endpoint filters to include address (legacy behavior) |
| Source enum | Allow `manual`, `excel`, `scraper`, `import` values |
| Status mapping | Document `is_active=false` ↔ `inactive`; soft delete ↔ `archived` |

Sprint 1.4 import module should mirror legacy `ImportBatch` / `ImportRow` field names (English) and status enums above.

---

## 10. Platform reusability check (ADR-009)

| Legacy capability | Owner |
|-------------------|-------|
| Auth, org, RBAC | KYROX Core (done) |
| Audit append | KYROX Core API (done) |
| Permission check | KYROX Core API (done) |
| Excel file parsing library | fair-crm product (domain-specific adapter) |
| Duplicate scoring algorithm | fair-crm product (CRM-specific) |
| Generic file storage for uploads | Evaluate Core file service when available — **report first** |

---

## 11. Phase 1 exit criteria (this item)

- [x] fuar-crm reference reviewed
- [x] Findings documented (this file)
- [ ] CUSTOMER_DESIGN.md updated with field gaps (optional CTO review)
- [ ] Sprint 1 Phase 2 implementation (not started)

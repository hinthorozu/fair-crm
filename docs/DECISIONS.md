# Architecture Decisions

## ADR-001 — Use `fair-crm` as the product repository name

Status: Accepted

The previous repository name `fuar-crm` is Turkish. The new product repository uses `fair-crm` to align with backend, API, database, and domain naming standards.

Frontend labels and user-facing messages remain Turkish.

## ADR-002 — Use KYROX Core for platform capabilities

Status: Accepted

FAIR CRM must not reimplement authentication, authorization, organization, membership, audit, settings, background jobs, or notifications.

Those concerns belong to KYROX Core.

## ADR-003 — Customer is the first aggregate, not Company

Status: Accepted

The first CRM aggregate is `Customer` rather than `Company`.

Reason:

FAIR CRM must support exhibitors, leads, suppliers, sponsors, organizers, partners, and other CRM account types. `Company` is too narrow and may cause future model drift.

Company/legal information will be represented as fields within the Customer aggregate.

## ADR-004 — Old `fuar-crm` remains reference-only

Status: Accepted

The old `fuar-crm` repository can be used as a reference for workflows, fields, and existing business assumptions.

It should not be used as the target architecture.

## ADR-005 — Import must use preview and merge decision workflow

Status: Accepted

Imported data must not be blindly inserted.

The product must support:

- Import preview
- Duplicate detection
- Possible match suggestions
- Merge/update decisions
- Row-level validation

## ADR-006 — Backend/API/database naming is English, frontend user-facing text is Turkish

Status: Accepted

This convention is inherited from KYROX project standards.

## ADR-007 — KYROX Core as independent platform service

Status: Accepted (revised)

KYROX Core **v0.4.0** is an **independent reusable backend platform service**. FAIR CRM is an **independent product service**. They run as **separate deployments**.

Rules:

- Integrate with Core through **public HTTP APIs** (and later SDK/events when available).
- Do **not** import kyrox-core Python modules (`app.modules.*`, `app.db.*`, etc.).
- Do **not** share SQLAlchemy Session or database with Core.
- Do **not** mount Core routers inside the Fair CRM application.
- Do **not** create cross-repository database foreign keys.

Rationale:

- Core is a platform service consumed by products through documented contracts.
- Clear deployment, versioning, and ownership boundaries between platform and product.
- Aligns with kyrox-core Backend Architecture Standards: products integrate via public API.

Local JWT validation using the same `JWT_SECRET_KEY` configuration is permitted — this is config alignment, not a Core code import.

See [INTEGRATION_WITH_CORE.md](INTEGRATION_WITH_CORE.md).

## ADR-008 — Fair CRM as separate FastAPI service (internal modular monolith)

Status: Accepted (revised)

FAIR CRM runs as its **own FastAPI service**, separate from KYROX Core. Internally it is a **modular monolith**: one product codebase, one process, layered modules under `backend/app/modules/`.

Rules:

- Fair CRM and Core have **different base URLs**, **different databases**, and **independent deploy units**.
- Product modules follow layered architecture (domain → application → infrastructure → api), aligned with kyrox-core conventions.
- Core platform routes (auth, orgs, audit query, settings, jobs, notifications) are **not** served by Fair CRM — clients call Core directly.
- Extraction of Fair CRM internal modules into separate services is allowed later if required — Core remains a separate platform service regardless.

See [ARCHITECTURE.md](ARCHITECTURE.md).

## ADR-009 — Evaluate platform reusability before every new feature

Status: Accepted

Before implementing any new Fair CRM business feature, evaluate whether the capability is **generic platform infrastructure** reusable across KYROX products.

Rules:

1. **Evaluate first** — During Phase 1 design (before Phase 2 code), ask: could another product (not only Fair CRM) need this without CRM-specific semantics?
2. **If platform-generic** — Stop Fair CRM implementation. Document the need and **propose it for KYROX Core** first. Wait for approval and Core delivery (or an explicit decision to defer) before continuing in fair-crm.
3. **If product-specific** — Proceed in fair-crm. CRM domain logic, fair/exhibitor workflows, and Fair CRM permission semantics stay here.
4. **Integrate via Core APIs** — When Core already provides the capability, consume it through public APIs; do not reimplement or duplicate in fair-crm.

Examples:

| Capability | Owner |
|------------|-------|
| Auth, RBAC, audit write, settings, jobs, notifications | KYROX Core |
| Customer, import pipeline, duplicate merge, fair participation | Fair CRM |
| New generic permission-check pattern, file storage, webhooks | Evaluate → likely Core |

Report platform needs in design docs (see [ARCHITECTURE.md](ARCHITECTURE.md) §13) and track in kyrox-platform before changing kyrox-core.

## ADR-010 — Hall / Stand on CustomerFairParticipation, not Customer or Fair

Status: Accepted (Sprint 06)

Fair-specific exhibitor data (hall, stand, fair-specific notes) belongs on the **CustomerFairParticipation** join entity, not on Customer or Fair aggregates. Import engine will resolve/create participations and write hall/stand there.

## ADR-011 — Future Activity ↔ Participation link (deferred)

Status: Proposed — not implemented in Sprint 06

Activities may later reference an optional `participation_id` to tie timeline entries to a specific fair visit/exhibitor context. No schema change in Sprint 06; add when activity UX requires fair-scoped filtering.

## ADR-012 — Fair Context Required for Imports

Status: Accepted (Sprint 07 Smart Import Wizard design)

**Decision:**

Smart Import batches must be associated with a selected Fair. The import source will not provide or resolve `fair_name`.

**Rationale:**

In real workflows, exhibitor lists are collected for a known fair. Requiring Fair context prevents incorrect fair matching and ensures hall/stand data is stored on CustomerFairParticipation.

**Consequences:**

- Import Wizard requires Fair selection (Screen 3).
- `fair_name` is not a supported mapping field.
- Duplicate detection must evaluate both Customer and CustomerFairParticipation.
- Hall/Stand belong to participation records, not Customer or Fair.
- Import batch persists `fair_id` for the entire batch.
- Alternative entry from Fair Detail pre-fills Fair context.

## ADR-014 — Detail Page Action Standard

Status: Accepted (Sprint 08.1)

**Decision:**

Every Detail page must expose a shared **Action Bar** inside `PageHeader`. Core CRUD and related workflows (edit, add contact, add participation, import, archive) are available directly on the Detail screen without returning to the list view.

**Action variants:**

- Primary — Edit
- Secondary — Add, Import
- Danger — Archive (and Delete when applicable)

**Consequences:**

- `PageHeader` accepts structured `actions` and optional `breadcrumbs`.
- Customer Detail and Fair Detail implement the full action set per entity.
- List screens remain for browse/search; they are not required for inline CRUD on an open record.
- Future Detail pages must follow the same pattern.

## ADR-015 — Universal Server-Side DataTable

Status: Accepted (Sprint 08.0)

**Decision:**

All Fair CRM list views must use server-side pagination, search, sorting, and filtering by default.

Client-side list operations (`sort()`, `filter()`, `slice()`) are allowed only for small static/local lists (enum dropdowns, ~20–30 item pickers).

**Rationale:**

The CRM now contains 28,000+ customers and 29,000+ fair participations. Fetching all records and filtering/sorting in the browser is not scalable.

**Consequences:**

- All new list endpoints must support the shared query contract (`page`, `pageSize`, `search`, `sort`, `direction`, entity filters).
- All list responses follow the shared paginated response format (`items`, `pagination`, `sorting`, `filters`).
- Frontend list views must use the shared `DataTable` / `useServerDataTable` infrastructure.
- New list screens are not complete unless they include server-side pagination, search, sort, filter (or a documented exception), URL state, loading, empty, and error/retry states.

## ADR-016 — Universal Import Standard & Data Integration Module

Status: Accepted (Sprint 09.0 — architecture)

**Decision:**

Fair CRM adopts a **Universal Import Standard** under a dedicated **Data Integration** module. All external data ingestion (Excel today; additional sources later) follows a single preview-first pipeline: Batch → File Analysis → Header Mode → Column Mapping → Normalization → Smart Matching → Preview → Decision → Background Import → Final Report.

**Module naming:**

| Layer | Name |
|-------|------|
| Backend module / API / database | `data_integration` (English) |
| Frontend menu label | **Veri Entegrasyonu** (Turkish) |
| Primary route | `/data-integration` |

**Import source priority** (implementation and UX ordering):

1. **Excel** — first-class; Sprint 07 wizard evolves into this module
2. **Web Scraper** — planned adapter (menu item disabled until shipped)
3. **CSV**
4. **XML**
5. **JSON**
6. **REST API**
7. **ERP** — connector-based; lowest priority

**Excel header mode (mandatory on batch setup):**

| Mode | Turkish UI | Behavior |
|------|------------|----------|
| `first_row_header` | İlk satır başlık | Row 1 = headers |
| `no_header` | Başlık yok | Columns A/B/C/D… with sample values in mapping |
| `manual_header_row` | Başlık satırını ben seçeceğim | User selects header row |

**Core rules (non-negotiable):**

- Import is **not** direct insert (extends ADR-005).
- Batch-level **`fair_id` required** (extends ADR-012); no `fair_name` resolution.
- Hall/stand on **CustomerFairParticipation** only (ADR-010).
- **No CRM writes** until user confirms preview decisions.
- Apply runs as a **background job** with final report.
- Merge is **additive and conservative** — see [docs/import/MERGE_RULES.md](import/MERGE_RULES.md).

**Frontend navigation (Veri Entegrasyonu):**

| Item | Initial status |
|------|----------------|
| Import İşleri | Active (wizard migrates from `/imports`) |
| Import Geçmişi | Planned |
| Mapping Şablonları | Planned |
| Web Scrapers | 🚧 Disabled |
| Export İşleri | 🚧 Disabled |
| API Entegrasyonları | 🚧 Disabled |
| ERP Entegrasyonları | 🚧 Disabled |
| CSV/XML Kaynakları | 🚧 Disabled |
| Senkronizasyon İşleri | 🚧 Disabled |
| Entegrasyon Ayarları | 🚧 Disabled |

**Rationale:**

Sprint 07 delivered Excel import and merge preview. Sprint 09.0 formalizes a source-agnostic standard so CSV, API, scraper, and ERP connectors plug into one pipeline without one-off import paths.

**Consequences:**

- Canonical docs: [docs/import/IMPORT_ARCHITECTURE.md](import/IMPORT_ARCHITECTURE.md), [MERGE_RULES.md](import/MERGE_RULES.md), [MATCHING_RULES.md](import/MATCHING_RULES.md).
- Existing `/imports` and `/api/v1/imports/*` remain until migration sprint; new work targets Data Integration naming.
- Import/export/sync **background jobs** share a common job pattern.
- Backend/API/database naming stays **English**; frontend stays **Turkish** (ADR-006).

## ADR-017 — Universal Source Adapter Framework

Status: Accepted (Sprint 09.2)

**Decision:**

Data Integration adopts a **Universal Source Adapter Framework**. External data sources are pluggable adapters sharing one lifecycle (`Connect → Read → Normalize → Preview`). The **Import Engine** is source-agnostic: mapping, matching, merge, and apply never depend on Excel, scraper, or ERP specifics.

**Adapter registration:**

- `SourceAdapter` protocol — `domain/source_adapter.py`
- `SourceAdapterRegistry` — resolve adapter by `ImportSourceType` or file extension
- Excel is the first registered adapter (`ExcelSourceAdapter`); new sources register without engine changes

**Scraper rule:**

One adapter per fair site (e.g. TUYAP, IFM). Each adapter owns URL structure, parsing, and pagination. Output is normalized to the same preview contract as file adapters.

**Non-negotiable:**

- Adapters **never** write CRM domain data
- Import Engine **never** imports site-specific scraper or ERP logic
- New source = new adapter + registry entry + tests

**Rationale:**

Sprint 09.1 shipped Excel import under a provisional `ImportAdapter`. Sprint 09.2 formalizes the platform model described in the product vision so CSV, API, scraper, and ERP connectors can ship incrementally.

**Consequences:**

- Canonical doc: [docs/import/SOURCE_ADAPTER_FRAMEWORK.md](import/SOURCE_ADAPTER_FRAMEWORK.md)
- Upload and sheet selection resolve adapters via registry
- Background apply jobs use FastAPI `BackgroundTasks` (commit before job runs)
- Future menu items (Web Scrapers, ERP, CSV/XML) map 1:1 to adapter families

## ADR-018 — System Administration Module Foundation

Status: Accepted (Sprint 09.2.2)

**Decision:**

Fair CRM introduces a **System Administration** module (`system_admin`) as the long-lived home for operational tooling. Sprint 09.2.2 delivers **Database Backups** as the first component; future items (Restore, Background Jobs, Audit Logs, Health Monitoring, Storage, Maintenance Mode, Scheduler, Disaster Recovery) extend the same module without one-off admin pages.

**Architecture:**

- Shared backup engine at `app/shared/database_backup` — no duplicated dump logic between dev scripts and Admin API
- Backup metadata in PostgreSQL (`system_backups`); files on disk under gitignored `backups/` (`faircrm_backup_YYYYMMDD_HHMMSS.dump`)
- Background jobs via FastAPI `BackgroundTasks` with stage progress (preparing → dumping → compressing → completed/failed)
- Admin-only permissions (`fair_crm.admin.backups.*`); download enforces path safety and permission checks
- **Restore** foundation (`RestoreService`, disabled endpoint, feature flag) — not enabled in this sprint

**Rationale:**

Real customer data requires safe, repeatable snapshots before import/migration. Dev-only scripts (Sprint 09.2.1) proved the workflow; this sprint productizes it as the first System Admin capability with production-grade extensibility.

**Consequences:**

- Admin menu: **Admin → System → Database Backups** (`/admin/system/backups`)
- API: `/api/v1/admin/backups/*`
- Dev PowerShell scripts delegate to `python -m app.shared.database_backup`
- Restore remains disabled until explicitly enabled via configuration

## ADR-019 — Universal Server-Side DataTable Sorting Rule

Status: Accepted (Sprint 09.2.3)

**Decision:**

All Fair CRM list screens using the Universal Server-Side DataTable standard (ADR-015) must expose **server-side sorting on every data column except Actions**. The Actions column is never sortable. This is mandatory — not optional per screen.

**Rules:**

- Frontend: `UniversalDataTable` with column definitions; `sortable: true` on data columns, `sortable: false` on Actions only.
- Hook: `useServerDataTable.setSort` — asc → desc → default cycle; URL sync via `sort_by` + `sort_order`.
- Backend: per-entity `ALLOWED_SORT_FIELDS` whitelist; `parse_list_query` + safe fallback for invalid `sort_by` (no HTTP 400).
- API: canonical query params `sort_by`, `sort_order`; response includes nested `sorting: { field, direction }`.
- Legacy aliases `sort`, `direction`, `sort_dir` remain accepted for backward compatibility.

**Rationale:**

Partial column sorting and manual `renderSortableHeader` per screen created inconsistent UX and duplicated boilerplate. A single component + column config scales to Admin/System modules and future list screens.

**Consequences:**

- `UniversalDataTable` component replaces manual header wiring.
- Activities list migrated from timeline to sortable table.
- Constitution documents the rule under **Universal Server-Side DataTable Standard — Sorting Rule**.
- Exceptions require a new ADR in this file.

---

## ADR-020: Customer hard-delete cascades related CRM rows

**Status:** Accepted  
**Date:** 2026-07-01

**Context:**

Operators may hard-delete a customer row directly in PostgreSQL (e.g. Navicat). Previously, foreign keys on `crm_contacts`, `crm_activities`, and `crm_customer_fair_participations` used `ON DELETE RESTRICT`, blocking deletion or leaving orphaned data.

**Decision:**

- `customer_id` foreign keys on contacts, activities, and participations → `ON DELETE CASCADE`.
- Optional `contact_id` / `primary_contact_id` references → `ON DELETE SET NULL` (contact-only deletes do not block; customer delete removes contacts and their dependents via cascade).
- Import row audit links (`match_*`, `created_*`, `updated_*` for customers and participations) → `ON DELETE SET NULL` (migration `0013_import_row_customer_fks`); import batches and fairs are never deleted with a customer.
- `fair_id` on participations remains `RESTRICT` (fairs are not deleted with a customer).
- Application API continues to **archive** customers (`deleted_at`); CASCADE applies to **hard SQL deletes** only.

**Consequences:**

- Alembic migration `0012_customer_cascade_delete` alters core CRM FK constraints.
- Alembic migration `0013_import_row_customer_fks` clears orphan import links and adds SET NULL FKs.
- SQLAlchemy models mirror the same `ondelete` values for future schema generation.
- Integration tests verify hard delete removes child rows, nulls import links, and preserves fairs/batches; archive leaves children intact.

---

## ADR-021: Backup format strategy and Universal Data Package foundation

**Status:** Accepted  
**Date:** 2026-07-02

**Context:**

Admin Database Backups initially supported only PostgreSQL custom-format dumps (`.dump`) for disaster recovery. Operators also need plain SQL for external tools and a vendor-independent export path for future CRM migrations.

**Decision:**

- Three backup formats, selected at create time:
  - `postgresql_dump` — DR restore via `pg_restore` (unchanged default)
  - `postgresql_sql` — `pg_dump --format=plain`, export/inspection only
  - `universal_data_package` — ZIP with JSON entities + `manifest.json`, export/migration only
- Metadata: `system_backups.backup_format`, optional `manifest_json` (migration `0014`)
- `UniversalDataPackageService` builds MVP ZIP (customers, fairs, participations, contacts, activities, metadata, manifest)
- Download serves the artifact matching `backup_format`; path traversal and admin permissions unchanged
- **Restore API remains `.dump`-only and disabled (501)** — SQL and ZIP are not restore targets

**Consequences:**

- Shared engine extended with `pg_dump_plain` and format-aware filename/path rules (`.dump`, `.sql`, `.zip`)
- Admin UI format picker in New Backup modal; list shows format column
- Dev PowerShell scripts continue to default to `.dump` for DR

---

## ADR-022: System Administration & Business Continuity Roadmap

**Status:** Accepted (Architecture — documentation sprint 09.2.5)  
**Date:** 2026-07-02

**Context:**

Database Backup Workspace (Sprint 09.2.2) and backup format options (09.2.4) established the first System Admin capability. The product needs a **1–2 year official roadmap** for System Administration and Business Continuity so implementation sprints do not collapse policy, history, DR, and export into a single monolithic backup feature.

**Decision:**

1. **System Administration vision** — Admin → System expands to: Dashboard, Database Backups, Backup Policies, Backup Jobs, Backup History, Disaster Recovery, Background Jobs, Audit Logs, Health Monitoring, Scheduler, Maintenance Mode, Storage Management, Environment Information, Cache Management, License, System Settings.

2. **Business Continuity** — Named sub-domain under System Administration covering: Database Backups, Backup Policies, Disaster Recovery, Restore, Backup Verification, Retention Policies, Remote Backup, Cloud Backup.

3. **Separate bounded contexts** — Database Backup, Backup Policy, Backup History, Backup Job, Disaster Recovery, Restore, Universal Data Package evolve as independent modules/use-case boundaries.

4. **Backup Policy Engine (future)** — Policies define *when*, *under what conditions*, *how many*, and *which format*; execution produces History rows. Default policies:
   - **Daily:** configurable time; retention 30; run only if `last_data_change > last_successful_backup`, else History **Skipped** / **No data changes**
   - **Weekly:** Monday; retention 10; evict oldest weekly when 11th would be created
   - **Monthly:** first day of month; retention 12 or Keep Forever (configurable)

5. **Backup History (future)** — Every run logged with status (Completed / Failed / Skipped), skipped reason, timestamps, duration, policy, trigger type, backup file reference, change-detected flag.

6. **Trigger types (future)** — Manual, Scheduled, Before Import, Before Restore, Before Migration, Before Upgrade, Application Update, Schema Migration.

7. **Retention strategy** — Policy-scoped cleanup after successful backup; **never** auto-delete the most recent successful backup.

8. **Formats** — Current: PostgreSQL Native (`.dump`), SQL (`.sql`), Universal Data Package (`.zip` MVP). Future delivery: cloud targets (S3, Azure Blob, GCS, NAS), remote backup orchestration.

9. **Universal Data Package** — Long-term vendor-independent migration export (`manifest.json` + entity JSON). **Not backup.** Restore path remains `.dump`-only.

10. **This ADR is roadmap-only** — No code, migration, or API in sprint 09.2.5.

**Rationale:**

Separating **artifact production** (Database Backup) from **operational rules** (Backup Policy) and **audit trail** (Backup History) prevents unmaintainable coupling in the shared dump engine and supports enterprise expectations (retention, skip-on-no-change, triggered pre-import backups).

**Consequences:**

- [PROJECT_STATUS.md](../PROJECT_STATUS.md) contains the phased delivery table (Foundation → Operations → Policy → DR → Platform admin).
- [docs/PRODUCT_VISION.md](PRODUCT_VISION.md) adds System Administration & Business Continuity platform vision.
- [PROJECT_CONSTITUTION.md](../PROJECT_CONSTITUTION.md) documents bounded-context rule for implementers.
- Implementation sprints reference ADR-022 when adding policy, history, or DR features.

---

## ADR-023: Tier-Based Product Delivery Strategy

**Status:** Accepted (Product Management — documentation sprint 09.2.6)  
**Date:** 2026-07-02

**Context:**

KYROX Fair CRM is growing across CRM features, data integration, system administration, and long-term platform vision. Without a delivery taxonomy, new ideas risk being implemented in ad-hoc order — UX polish before shared engines, or vision features before business foundations.

**Decision:**

Adopt a **four-tier product delivery model**. Every new feature, idea, or architectural initiative must be classified into exactly one tier **before** roadmap entry and sprint planning.

| Tier | Name | Scope (summary) |
|------|------|-----------------|
| **1** | Platform Foundation | Core architecture: auth/RBAC integration, universal UI/data engines, import/export/backup/job/notification infrastructure, scheduler, audit, health, storage, API & architecture standards |
| **2** | Business Features | CRM business value: customers, fairs, participations, activities, import/merge, scrapers (TUYAP, IFM, F Istanbul), reporting, dashboard, statistics |
| **3** | User Experience | KYROX Design System, responsive layout, universal wizard/cards/modal, animations, dark theme, accessibility, keyboard shortcuts, empty/loading/progress states, typography, spacing, design tokens |
| **4** | Future Vision | Long-term: AI assistant, workflow engine, automation, cloud sync, marketplace, plugins, REST/webhooks, multi-tenant, BI, predictive analytics, Universal Data Package maturity, CRM migration toolkit |

**Planning rule:**

1. New idea arrives → determine **Tier**
2. Add to official roadmap ([PROJECT_STATUS.md](../PROJECT_STATUS.md))
3. Plan sprint — **do not** start implementation without tier assignment

**Implementation rule (default priority):**

```text
Tier 1  →  Tier 2  →  Tier 3  →  Tier 4
```

- Unfinished **Tier 1** work takes precedence over **Tier 3** UX initiatives.
- **Tier 2** ordering still follows business phases and P0/P1/P2 in [PRODUCT_VISION.md](PRODUCT_VISION.md).
- **Product owner** may change sprint priority; **tier reclassification** requires documented rationale in roadmap or ADR.

**Relationship to other models:**

- **Business Workflow (Phase A/B/C)** — applies primarily to **Tier 2**
- **ADR-022 Business Continuity** — mostly **Tier 1** (backup, policy, DR, restore)
- **Platform Thinking (Import, Intelligence, AI)** — Tier 1 engines + Tier 2/4 capabilities

**This ADR is standards-only** — No code, migration, or API in sprint 09.2.6.

**Consequences:**

- [PROJECT_CONSTITUTION.md](../PROJECT_CONSTITUTION.md) — Tier planning rules for all contributors
- [PROJECT_STATUS.md](../PROJECT_STATUS.md) — Tier definitions, snapshot, sprint roadmap tags
- [PRODUCT_VISION.md](PRODUCT_VISION.md) — Tier section + P0/P1/P2 interaction
- Future sprint proposals must state target **Tier** in planning docs

---

## ADR-024: Universal Import Mapping Preview

**Status:** Accepted (Sprint 09.3)  
**Date:** 2026-07-02

**Context:**

The Import Wizard column mapping step showed only column names (e.g. "Firma (A)", "Telefon (B)"). Users could not see actual cell values before mapping, making headerless files, wrong headers, and ambiguous columns error-prone.

**Decision:**

Adopt the **Universal Import Mapping Preview Standard**:

1. Mapping UI uses **three columns**: CRM field → source column dropdown → live sample preview.
2. Server returns `mapping_columns` with up to **10** sample values per column (from first 10 data rows after header resolution).
3. New endpoint `GET /api/v1/data-integration/imports/{batch_id}/mapping-preview` recalculates samples when header mode or manual header row changes.
4. UI defaults to **3** visible sample rows; user may expand to 10. Empty cells display as `—`; long values truncate with tooltip.
5. Per-column **stats** (total, empty, filled, first value) shown in preview footer.

**Rationale:**

- Aligns with preview-first import philosophy (ADR-005, ADR-016).
- Source-agnostic contract for future adapters (CSV, API, scraper).
- Avoids shipping full Excel to client; samples computed server-side from stored `raw_preview_json`.

**Consequences:**

- [docs/import/IMPORT_MAPPING_STANDARD.md](import/IMPORT_MAPPING_STANDARD.md) — canonical spec
- [PROJECT_CONSTITUTION.md](../PROJECT_CONSTITUTION.md) — mapping preview rule under Universal Import Standard
- `column_mapper.build_mapping_preview_columns()` — shared builder for all source adapters
- Import Wizard mapping step UI updated in Sprint 09.3

---

## ADR-025: Excel Column Mapping Grid + Background Analyze Queue

**Status:** Accepted  
**Date:** 2026-07-02

**Context:**

The separate CRM-field→column mapping table did not match how users read Excel. Synchronous analyze blocked HTTP requests on large files. Multiple concurrent analyzes per organization risked CRM load spikes.

**Decision:**

1. **Grid mapping UI** — Excel rows in a table; each column header has a mapping dropdown (Kullanma / Firma Adı / …). `company_name` required; duplicate field assignment forbidden.
2. **Wizard setup flow** — upload → sheet → header → mapping grid → Import Jobs list (analyze removed from inline wizard).
3. **Lifecycle statuses** — `mapping_completed`, `analysis_queued`, `analyzing`, `decision_required`, `analysis_failed`, `completed`, etc.
4. **Background analyze** — `POST /data-integration/imports/{id}/analyze-job` returns 202; work runs in FastAPI BackgroundTasks.
5. **Organization lock** — at most one active analyze job (`queued`/`running`) per organization; HTTP 409 on conflict.
6. **Matching scope** — company_name only (no phone/email/website scoring in this sprint).

**Consequences:**

- Sync `POST .../analyze` deprecated for production use
- [docs/IMPORT_MAPPING_GRID_COMPLETION.md](IMPORT_MAPPING_GRID_COMPLETION.md)
- Migration `0015_import_batch_lifecycle`

---

## ADR-026: Company Name Matching — Turkish Normalize + Token Scoring

**Status:** Accepted  
**Date:** 2026-07-02

**Context:**

Fair catalogs often list only company names with inconsistent legal suffixes, abbreviations, and Turkish character variants. Phone/email/website are frequently absent. Matching must be reliable on `company_name` alone.

**Decision:**

1. **Turkish normalization** — İ/I/ı/i and ş/ğ/ü/ö/ç mapped to ASCII; punctuation and dotted abbreviations normalized.
2. **Legal suffix handling** — phrase stripping on full key; core token comparison excludes suffix tokens (not sector words like GIDA).
3. **Token + string scoring** — Jaccard/overlap/SequenceMatcher with confidence bands: 95+ exact, 85–94 fuzzy, 70–84 weak, <70 none.
4. **False-positive guards** — first-token and distinctive-tail mismatch rules.
5. **Explanations** — stored in `normalized_data_json._match_explanation` for decision UI.

**Consequences:**

- `company_name_matcher.py`, enhanced `company_name_normalizer.py`
- [docs/COMPANY_NAME_MATCHING_COMPLETION.md](COMPANY_NAME_MATCHING_COMPLETION.md)

---

## ADR-027: Import Job Resume Flow + Bulk Decision Preview/Apply Jobs

**Status:** Accepted  
**Date:** 2026-07-02

**Context:**

Upload and wizard were coupled: users could not safely leave mid-setup. Bulk decision buttons applied changes immediately without confirmation counts. Large batches needed non-blocking bulk operations with concurrency control.

**Decision:**

1. **Upload → Job** — after upload, redirect to Import Jobs list; batch stays `uploaded`; file immutable on same batch.
2. **Devam Et** — resume from list by status: setup steps (`uploaded`→sheet, `sheet_selected`→header, `header_configured`→mapping) or `decision_required`→decisions.
3. **Bulk preview** — `POST .../bulk-actions/preview` returns `affected_rows` + `summary` without writes.
4. **Bulk apply job** — `POST .../bulk-actions/apply` returns 202; `ImportJobType.BULK_DECISION` background runner.
5. **Locks** — one active `bulk_decision` or `apply` job per batch (HTTP 409).
6. **Idempotency** — rows with existing `decision` skipped on bulk apply.

**Consequences:**

- [docs/IMPORT_RESUME_BULK_COMPLETION.md](IMPORT_RESUME_BULK_COMPLETION.md)
- Batch API extended with resume metadata (`available_sheets`, `column_mapping_json`, …)
- Frontend `importResume.ts` + confirm dialog before bulk apply

---

## ADR-028: Universal Modal Standard

**Status:** Accepted  
**Date:** 2026-07-02

**Context:**

Users lost form data when modals closed accidentally via backdrop click or Escape. Long CRM forms (customer, fair, activity, import, backup) made this costly.

**Decision:**

1. **Shared `Modal` and `ConfirmDialog`** are the only overlay primitives for product dialogs.
2. **No implicit close** — backdrop click and Escape do not dismiss modals or confirm dialogs.
3. **Explicit close only** — X, İptal/Vazgeç, Kaydet/Tamam (after success), or system-initiated close after completed operations.
4. **Dirty guard** — forms inside `Modal` report dirty state via `useReportFormDirty`; attempting to close with unsaved changes shows:
   - Message: *Kaydedilmemiş değişiklikler var. Çıkmak istediğinize emin misiniz?*
   - **Forma Dön** (keep modal open) / **Çık** (discard)
5. **Clean forms** close immediately on X or İptal without confirmation.

**Implementation:**

- `frontend/src/components/ui/Modal.tsx` — dirty context + nested discard `ConfirmDialog`
- `frontend/src/components/ui/ConfirmDialog.tsx` — button-only dismiss
- `frontend/src/hooks/useModalForm.ts` — `useReportFormDirty`, `useModalFormCancel`
- All entity forms (`CustomerForm`, `FairForm`, `ActivityForm`, `ContactForm`, `ParticipationForm`) and admin backup create modal use the hooks.

**Consequences:**

- New screens must use shared `Modal`; no custom backdrop-close overlays.
- `.cursor/rules/shared-modal-focus.mdc` updated to reflect ADR-028.

---

## ADR-029: Universal Decision Queue Standard — Bulk Decision Assignment

**Status:** Accepted  
**Date:** 2026-07-03

**Context:**

Decision Queue screens require row-by-row dropdown changes for large batches. Users need to select rows and assign a decision in bulk without writing CRM data. Final execution (customer create/update, participation, skip) must remain a separate explicit apply step.

**Decision:**

1. **Row selection** — per-row checkbox + master checkbox (current page only); selection persists across pagination via ID set.
2. **Bulk Decision panel** — operation select (`create_new`, `update_existing`, `skip`) + **SEÇİLİ KAYITLARA UYGULA**; updates `decision` only, no CRM writes.
3. **Manual override** — per-row dropdown remains editable after bulk assignment.
4. **Final apply** — **TÜM LİSTEYİ UYGULA** executes CRM changes for the current filter/search pending scope via `POST .../decisions/apply`.
5. **API** — extend `PATCH .../rows/bulk-decision` with `{ row_ids, decision }` (legacy `action` presets retained for scripts).
6. **Response** — `updated_count`, `skipped_count`, `errors[]` for rows that cannot receive the requested decision (e.g. `update_existing` without match).
7. **Universal pattern** — Selection → Bulk Decision → Manual Override → Final Apply applies to Import and future Decision Queue screens (duplicate resolution, lead decision, cleanup, approval, archive).

**Consequences:**

- Import Decision UI: bulk panel above list; final apply button always uses full scoped apply.
- Reuses `SetImportRowDecisionUseCase` per selected row for consistent validation and row status updates.

**Apply result UX (extension):**

1. **Success summary** — `processed_count` + `not_processed_count` only; no row list for undecided rows.
2. **`not_processed_count`** — rows without decision (or manual review); not errors, not warnings.
3. **`errors[]`** — real execution failures only (DB, validation, constraint, unexpected exception).
4. Frontend shows ✅ processed, ℹ not processed, ⚠ failed with row details only for execution errors.

---

## ADR-030: Internal Customer Cleanup Utility

**Status:** Accepted  
**Date:** 2026-07-03  
**Detail:** [CUSTOMER_CLEANUP_ARCHITECTURE.md](CUSTOMER_CLEANUP_ARCHITECTURE.md)

**Context:**

Master DB accumulated duplicate customers from migration and imports. A one-time internal cleanup may be needed before taking a clean backup. This is **not** a tenant-facing product module.

**Decision:**

1. **Internal maintenance workflow only** — future CLI/script; no tenant UI, no Cleanup Queue platform.
2. **Import flow untouched.**
3. **No schema implementation yet** — no migration `0016`, no cleanup/suppression tables, no `crm_customers` merge/delete columns, no merge event table.
4. **Future option** — an Excel Import-like review UI may be considered later; not committed.
5. **Design principles (when implemented)** — operator-driven merge; fair participation must not be lost; no automatic merge.

**Out of scope:**

Tenant screens, Cleanup Queue platform, suppression persistence, continuous data quality, broad REST API, automatic merge, merge undo.

**Consequences:**

- No customer-cleanup code or DB migration until explicitly scoped.
- When a maintenance tool exists, operators run it with backup before/after.

---

## ADR-031: Defer communication-table indexes until Phase 2 performance review

**Status:** Accepted — deferred work  
**Date:** 2026-07-03  
**Detail:** [CUSTOMER_COMMUNICATION_PERFORMANCE.md](CUSTOMER_COMMUNICATION_PERFORMANCE.md)

**Context:**

Customer phone, email, and website data moved to child tables (`crm_customer_phones`, `crm_customer_emails`, `crm_customer_websites`) in migration `0020`. Import, duplicate analysis, and merge flows will increasingly query these tables. The current dataset is small and matching/merge rules are still evolving.

**Decision:**

1. **Do not add indexes now** on normalized phone, email, or domain values.
2. **No schema migration** for performance until the Phase 2 Performance Review is triggered.
3. **Document future work** — triggers, `EXPLAIN ANALYZE` targets, and candidate indexes live in `CUSTOMER_COMMUNICATION_PERFORMANCE.md`.

**Triggers for Phase 2 review:**

- Customer count > 100,000
- Import batch > 50,000 rows
- Duplicate analysis or merge becomes slow

**Consequences:**

- Phase 1 ships without extra communication indexes; acceptable at current scale.
- Before large-scale production load, run the documented review and add indexes only with measured justification.

---

## ADR-032: Global Responsive UI Design System

**Status:** Accepted  
**Date:** 2026-07-21  
**Detail:** [docs/frontend/RESPONSIVE_UI_STANDARD.md](frontend/RESPONSIVE_UI_STANDARD.md)

**Context:**

Sprint 04.5 delivered reusable UI primitives and Sprint 08.0/ADR-015/ADR-019 delivered Universal Server-Side DataTable. Screens still diverged: some used page-local mobile cards, technical fields appeared in main tables, form grids were 2→1 only, and “desktop works” was treated as enough. Horizontal scroll became the default escape hatch for wide tables.

**Tier note (ADR-023):** This is Tier 3 UX work. Product owner explicitly scoped Global Responsive UI as mandatory for all current and future screens — accepted override over open Tier 1 gaps for this delivery.

**Decision:**

1. **One responsive standard** for all Fair CRM frontend screens (list, form, filter, modal, card, pagination, actions).
2. **Breakpoints** — mobile `<768` (smoke 390), tablet `768–1023`, laptop `≥1024`, desktop polish `≥1440`.
3. **Form / filter grid** — desktop 3 columns, tablet 2, mobile 1 via `FormGrid` / `FilterPanel`.
4. **ResponsiveDataTable** under `UniversalDataTable` with column `priority`: `primary` | `secondary` | `technical`.
5. **No default horizontal scroll** — `table-wrap--scroll-only` is opt-in only.
6. **Technical fields** (`run_id`, UUID, `adapter_key`, long URL, JSON/debug) never primary main-table columns.
7. **Modal** — centered desktop, wide tablet, bottom-sheet mobile with sticky footer; ADR-028 dirty guard unchanged.
8. **Shared components only** — extend existing primitives; no page-local margin hacks as the design system.

**Implementation:**

- `ResponsiveDataTable`, `FilterPanel`, `TruncatedText`, `TechnicalDetails`, `RadioField`
- `UniversalDataTableColumn.priority`
- CSS tokens and ADR-032 section in `frontend/src/styles.css`
- Priority screens migrated: Enrichment, Todos, Run History, Customers, Fairs, Follow-ups, Imports, Dashboard

**Consequences:**

- Every new frontend screen must pass the Responsive UI Definition of Done in `PROJECT_CONSTITUTION.md` and `docs/frontend/RESPONSIVE_UI_STANDARD.md`.
- Remaining admin/mail screens adopt the standard as they are touched.


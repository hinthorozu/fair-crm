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


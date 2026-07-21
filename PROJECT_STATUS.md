# KYROX Fair CRM — Project Status

**Living status document** — updated automatically after every completed sprint.

| Field | Value |
|-------|-------|
| **Current Version** | v0.9.4 (Backup Format Options) |
| **Last updated** | 2026-07-21 (Central Activities + hard delete) |
| **Constitution** | [PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md) |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |
| **Product Vision** | [docs/PRODUCT_VISION.md](docs/PRODUCT_VISION.md) |

---

## Quality Gate

| Check | Status |
|-------|--------|
| Backend tests | **210 PASS** |
| Frontend build | **PASS** |
| Migration `0010_data_integration` | **APPLIED** (PostgreSQL) |
| Migration `0011_system_backups` | **APPLIED** (PostgreSQL) |
| Migration `0014_backup_format_options` | **READY** (PostgreSQL) |
| Runtime verification (Sprint 09.2.2) | **PASS** — migration, reset-dev, Swagger, live API, live UI |
| Dev auto-start (`dev-start.ps1`) | **PASS** — idempotent; Windows reboot verified manually |
| Import mapping grid + analyze queue | **PASS** — grid UI, background analyze, org lock (74 backend tests) |
| Company name matching stabilization | **PASS** — Turkish normalize, token scoring (90 import tests) |
| Import resume flow + bulk decision jobs | **PASS** — Devam Et, preview/apply bulk, batch locks |
| Legacy UMCRM dev migration | **APPLIED** (115 fairs, 28,155 customers, 29,561 participations) |

---

## Development Runtime

| Script | When to use |
|--------|-------------|
| `.\scripts\dev\dev-start.ps1` | After Windows or Docker Desktop restart — one command brings up Postgres + API + UI |
| `.\scripts\dev\dev-stop.ps1` | End of day — stops API/UI; add `-StopInfra` to stop Postgres container |
| `.\scripts\dev\reset-dev.ps1` | Stale port / hung uvicorn — force kill and restart |
| `.\scripts\dev\verify-dev-auto-start.ps1` | Automated validation (idempotency, health, port collision) |

Docker `postgres` service: `restart: unless-stopped`. Redis / worker / pgAdmin / MinIO are **not** in compose yet — `dev-start.ps1` skips optional waits when services are undefined.

Details: [docs/DEV_RUNTIME.md](docs/DEV_RUNTIME.md) · [docs/DEV_AUTO_START_COMPLETION.md](docs/DEV_AUTO_START_COMPLETION.md)

---

## Completed

### ✅ Central Activities Screen + Hard Delete (ADR-033)

**Completed Features**

- Org-wide Activities list at `/activities` (`GET /api/v1/activities`)
- Server-side filters: search, customer, activity type, status, date range
- Activity detail modal (customer, type/outcome, note, dates, todo/outcome, action flags)
- Single hard delete (`DELETE /api/v1/activities/{id}` → 204, physical row removal)
- Bulk hard delete (`POST /api/v1/activities/bulk-delete`) with selection + confirm + partial results
- UniversalDataTable / WidthResponsiveDataTable + dual pagination (ADR-032)
- Worklist `last_activity_id` SET NULL on delete (no silent cascade)
- Backend activity tests + frontend build verified

### ✅ Global Responsive UI Design System (ADR-032)

**Completed Features**

- Breakpoint tokens and shared CSS for form/filter 3/2/1 grids, FilterPanel, modal bottom-sheet, button aliases
- **List table standard:** `UniversalDataTable` → `WidthResponsiveDataTable` (available-width hide, order = priority, child rows) + dual pagination default
- `priority: "technical"` = detail-only forever; page-local responsive table hacks rejected
- Shared `FilterPanel`, `TruncatedText`, `TechnicalDetails`, `RadioField`
- All UniversalDataTable screens inherit the standard (Customers, Fairs, Todos, Follow-ups, Imports, Run History, Admin backups, Dashboard, …)
- Constitution Responsive UI Definition of Done + [docs/frontend/RESPONSIVE_UI_STANDARD.md](docs/frontend/RESPONSIVE_UI_STANDARD.md)
- Frontend-only; API contracts unchanged

### ✅ Sprint 01 — Customer Management

**Completed Features**

- CRUD
- Search
- Pagination
- Sorting
- Archive
- Restore
- Swagger
- Frontend
- Tests

### ✅ Sprint 02 — Fair Management

**Completed Features**

- CRUD
- Search
- Pagination
- Sorting
- Archive
- Restore
- Swagger
- Frontend
- Tests

### ✅ Sprint 03 — Customer Contacts

**Completed Features**

- Contact CRUD (create, read, update, soft delete)
- List contacts by customer
- Primary contact rule (one per customer)
- Multi-email support (`;` separated, comma accepted on input)
- Full name computed in API response
- Swagger
- Customer detail page with İletişim Kişileri tab
- Turkish frontend labels
- Tests

### ✅ Sprint 04 — Customer Activities

**Completed Features**

- Activity CRUD (create, read, update; user delete is hard delete per ADR-033)
- List activities by customer (paginated, sortable) + org-wide central list
- Activity types: call, meeting, email, whatsapp, note, fair_visit, follow_up, other
- Activity status: open, completed, cancelled
- Activity source: manual (default), system, email_automation, whatsapp_integration, import, other
- Optional contact linkage with same-customer validation
- Follow-up date support
- Legacy `deleted_at` / `is_active` columns retained; new deletes physically remove the row
- Swagger
- Customer detail page with Aktiviteler tab + central `/activities` screen
- Turkish frontend labels and timeline list
- Backend tests
- Live API verification script

### ✅ Sprint 04.5 — UX & Navigation Foundation

**Completed Features**

- Sidebar navigation layout with top bar and breadcrumb
- Reusable UI components (Badge, EmptyState, LoadingState, ConfirmDialog, Modal, PageHeader, Tabs, Card, DataTable, FormField)
- Customer detail CRM layout with unified tabs (Genel Bilgiler, İletişim Kişileri, Aktiviteler)
- Activity timeline UI with type/status/source badges and follow-up highlight
- Standardized empty states, loading skeletons, and confirm dialogs
- Table hover/zebra styling and consistent color tokens
- Responsive sidebar and mobile-friendly forms/dialogs
- Search placeholder standardization
- Frontend build verified

### ✅ Sprint 06 — Customer Fair Participation

**Completed Features**

- `CustomerFairParticipation` entity and `crm_customer_fair_participations` table
- Many-to-many Customer ↔ Fair with hall, stand, participation status, notes, primary contact, visited_at
- Participation status enum (planned, exhibitor, visited, contacted, follow_up_required, not_interested, customer, other)
- Unique active customer + fair constraint; soft delete with recreate after delete
- Primary contact validation (same customer only)
- Archived customer/fair create blocked
- API: list by customer, list by fair, CRUD on `/fair-participations`
- Customer detail **Katıldığı Fuarlar** tab with add/edit/delete
- Fair detail page with **Katılımcı Firmalar** tab (clickable company → customer detail)
- Turkish labels and status translations
- Backend tests (12 scenarios) and live verification script
- Import-ready model: hall/stand on participation, not on Customer/Fair

### ✅ Sprint 07 — Smart Import Wizard Phase 1

**Completed Features**

- 9-step Smart Import Wizard UI at `/imports`
- Fair context required on batch (`fair_id`, ADR-012)
- Raw Excel upload without CRM writes
- Manual column mapping with headerless Excel support
- Separate analyze step (normalize → validate → duplicate detection)
- Two-level duplicate detection: Customer + Participation in selected Fair
- Apply: Customer + CustomerFairParticipation + Contact + Activity (source=import)
- Hall/stand/notes on participation only; `fair_name` not supported
- Bulk row decisions API
- Fair Detail → Katılımcıları İçe Aktar entry point
- Migration `0008_import_wizard`
- Backend tests (163 total) and frontend build

### ✅ Sprint 07.1 — Smart Merge Viewer & Cleanup

**Completed Features**

- Field-level merge diff viewer (expand/collapse per row) with CRM vs Import comparison
- Backend-generated merge summary per row (`merge_preview.summary_lines`)
- Entity-grouped merge preview: Customer, Fuar Katılımı, İletişim Kişisi
- Merge outcome badges: Aynı, Yeni, Eklenecek, Güncellenecek, Korunacak, Çakışıyor, Boş
- Preview filters (Tümü/Yeni/Güncellenecek/Duplicate/Hatalı/Atlanacak), search, sort
- Contact apply live verification (Customer + Participation + Contact + Activity)
- Legacy `POST /imports/customers/upload` marked deprecated (removal v0.9.0); backend tests retained
- Removed unused `ImportsPage.tsx`
- Backend tests (171 total) and frontend build
- Dev runtime reset: `scripts/dev/reset-dev.ps1` (see [docs/DEV_RUNTIME.md](docs/DEV_RUNTIME.md))

### ✅ Sprint 08.1 — Detail Page Action Standard

**Completed Features**

- `PageHeader` action bar API: typed `PageHeaderAction[]` with `primary` / `secondary` / `danger` variants; backward compatible with legacy `React.ReactNode`
- Breadcrumb back links in PageHeader (`← Müşterilere Dön`, `← Fuarlara Dön`)
- Customer Detail header actions: Düzenle, İletişim Kişisi Ekle, Fuara Ekle, Yeni Aktivite, Arşivle — available on every tab
- Fair Detail header actions: Düzenle, Katılımcı Firma Ekle, Katılımcıları İçe Aktar, Yeni Aktivite (disabled), Arşivle
- Edit customer/fair modals, contact/activity/participation forms, archive confirm — all from Detail screen without list navigation
- Fair Detail → Katılımcıları İçe Aktar opens Import Wizard at `/imports/fair/{id}`
- ADR-014 documented in [docs/DECISIONS.md](docs/DECISIONS.md)
- Frontend build and browser verification PASS

### ✅ Sprint 08.0 — Universal Server-Side DataTable Standard

**Completed Features**

- Shared list query contract: `page`, `pageSize`, `search`, `sort`, `direction`, entity filters (legacy aliases retained)
- Shared list response: `items`, `pagination`, `sorting`, `filters` on all list endpoints
- Server-side search/sort/filter on Contacts, Activities, Participations, Import rows
- Fair Participants optimized for 29k+ records (no client-side full-list operations)
- Migration `0009_list_indexes` for list performance
- Frontend `useServerDataTable` hook + URL state sync; sortable `DataTable` headers
- Migrated: Customers, Fairs, Customer Detail tabs, Fair Participants, Import Wizard preview
- ADR-015 + List Screen Definition of Done in constitution
- Backend tests (173) and frontend build PASS

### ✅ Legacy UMCRM Migration (Dev)

**Completed Features**

- Legacy analysis, cleaning, merge plan pipeline (`scripts/legacy/`)
- Dev domain reset: `reset_fair_crm_dev_domain.py`
- Migration engine: `migrate_umcrm_to_kyrox.py` (`--dry-run`, `--apply`)
- Idempotent UUID5 mapping + skip-on-reapply
- Full dev DB import from canonical JSON (no SQL dump re-parse)
- Documentation: [docs/LEGACY_UMCRM_MIGRATION.md](docs/LEGACY_UMCRM_MIGRATION.md)

---

## Long-Term Product Vision

KYROX Fair CRM is evolving from a fair CRM into a **Customer Data Platform** — continuously acquiring, enriching, verifying, and improving customer information with human approval at every CRM write.

| Topic | Document |
|-------|----------|
| **Full vision** | [docs/PRODUCT_VISION.md](docs/PRODUCT_VISION.md) |
| Customer Data Lifecycle | Acquire → Import → Research → Enrichment → Verification → Approval → CRM → Sales → Repeat |
| Business Phase A | Customer Acquisition (Universal Import Engine) — **current P0** |
| Business Phase B | Customer Enrichment (website, email, phone, WhatsApp, contact discovery) |
| Business Phase C | Fair Discovery (fair website → scraper → import → enrichment) |
| Long-term platforms | Import, Company Intelligence, Data Quality, AI, Integration |

Development priority is **business-value driven** (P0 → P1 → P2), not complexity-driven. See Product Vision for platform boundaries and philosophy.

---

## Current Sprint

**Sprint 09.3 — CSV Source Adapter** (planned)

Status: **Backlog** — next adapter after Excel foundation.

---

## Recently Completed

### ✅ Sprint 09.2.6 — Tier-Based Product Delivery Strategy (Product Management)

Status: **Completed** (documentation only — no code, migration, or API)

- Official **Tier 1–4** product delivery model for all future planning
- **ADR-023** — planning rules, implementation priority, tier definitions
- Updates: `PROJECT_STATUS.md`, `PROJECT_CONSTITUTION.md`, `docs/PRODUCT_VISION.md`, `docs/DECISIONS.md`

### ✅ Sprint 09.2.5 — System Administration & Business Continuity Roadmap (Architecture)

Status: **Completed** (documentation only — no code, migration, or API)

- Official 1–2 year roadmap for **System Administration** and **Business Continuity**
- ADR-022 — bounded contexts, policy engine, history, retention, triggers, future formats
- Updates: `PROJECT_STATUS.md`, `PROJECT_CONSTITUTION.md`, `docs/PRODUCT_VISION.md`, `docs/DECISIONS.md`, `CHANGELOG.md`

### ✅ Sprint 09.2.4 — Backup Format Options & Universal Data Package Foundation

Status: **Completed**

- Admin **New Backup** modal — format picker: `.dump` (DR), `.sql` (plain export), Universal Data Package `.zip` (MVP)
- Migration `0014_backup_format_options` — `backup_format`, `manifest_json` on `system_backups`
- Shared engine: `pg_dump_plain` for SQL; format-aware paths (`.dump`, `.sql`, `.zip`)
- `UniversalDataPackageService` — JSON entities + manifest ZIP (export/migration, not restore)
- List shows format column; download serves correct artifact
- Restore remains `.dump`-only and disabled (501)
- ADR-021

### ✅ Sprint 09.2.2 — Admin Database Backup Workspace

Status: **Completed** (Definition of Done satisfied)

- Shared Python backup engine (`app/shared/database_backup`) — single source for dev scripts and Admin API
- `system_admin` module — migration `0011_system_backups`, background backup jobs, metadata persistence
- Admin API `/api/v1/admin/backups/*` (create, list, get, download; restore foundation disabled)
- Frontend **Admin → System → Database Backups** at `/admin/system/backups`
- Progress stages: Preparing → Dumping → Compressing → Completed/Failed
- Permissions: `fair_crm.admin.backups.create|read|download`
- Runtime DoD: migration `0011`, reset-dev, Swagger, live API backup+download, live UI
- Backend tests (185) and frontend build PASS
- ADR-018 — System Administration module foundation

### ✅ Sprint 09.2.1 — Database Backup / Restore Standard (dev utility)

- PowerShell dev scripts delegate to shared Python engine (no duplicated dump logic)
- `scripts/dev/backup-db.ps1`, `restore-db.ps1`, `list-backups.ps1`, `db-backup-lib.ps1`

### ✅ Sprint 09.2 — Universal Source Adapter Framework

- `SourceAdapter` protocol and `SourceAdapterRegistry`
- `ExcelSourceAdapter` on formal lifecycle; upload/sheet select via registry
- Import Engine remains source-agnostic
- ADR-017 + [SOURCE_ADAPTER_FRAMEWORK.md](docs/import/SOURCE_ADAPTER_FRAMEWORK.md)
- Background apply job fix (commit before job execution)

### ✅ Sprint 09.1 — Data Integration Workspace & Universal Import Engine

Status: **Completed** (Definition of Done satisfied)

- Backend `data_integration` module — `ImportMapper`, `ImportValidator`, `DuplicateDetector`, `MergeStrategy`, `ImportExecutor`
- API `/api/v1/data-integration/*` (+ legacy `/api/v1/imports/*` alias)
- Excel header modes, sheet selection, background apply jobs (`crm_import_jobs`)
- Migration `0010_data_integration` applied on PostgreSQL
- Frontend **Veri Entegrasyonu** at `/data-integration`
- Runtime DoD: reset-dev, Swagger, live API script (4 scenarios), UI smoke
- Decisions: `participation_only`, `manual_review`

---

## Sprint Roadmap

Chronological plan — completed, active, and backlog sprints.

| Sprint | Module | Status |
|--------|--------|--------|
| 01 | Customer Management | Completed |
| 02 | Fair Management | Completed |
| 03 | Customer Contacts | Completed |
| 04 | Customer Activities | Completed |
| 04.5 | UX & Navigation Foundation | Completed |
| 05 | Customer Phones | Planned |
| 06 | Customer Fair Participation | Completed |
| 07 | Smart Import Wizard Phase 1 | Completed |
| 07.1 | Smart Merge Viewer & Cleanup | Completed |
| 08.0 | Universal Server-Side DataTable Standard | Completed |
| 08.1 | Detail Page Action Standard | Completed |
| **09.0** | **Data Integration & Universal Import Standard** | **Completed** |
| **09.1** | **Data Integration Workspace & Universal Import Engine** | **Completed** |
| **09.2** | **Universal Source Adapter Framework** | **Completed** |
| **09.2.2** | **Admin Database Backup Workspace** | **Completed** |
| **09.2.4** | **Backup Format Options & Universal Data Package (MVP)** | **Completed** |
| **09.2.5** | **System Admin & Business Continuity Roadmap (docs)** | **Completed** |
| **09.2.6** | **Tier-Based Product Delivery Strategy (docs)** | **Completed** |
| 09.3 | CSV Source Adapter | Planned (Tier 1 adapter + Tier 2 import) |
| 10.x | Customer Emails · Admin: Backup History & Restore | Planned |
| 11.x | Admin: Backup Policies & Retention | Planned |
| 12.x | Admin: DR, Remote/Cloud Backup · Reporting | Planned |

---

## Tier-Based Product Delivery Strategy

**Canonical ADR:** [ADR-023 — Tier-Based Product Delivery Strategy](docs/DECISIONS.md)

Every new idea, feature, or architectural decision is classified into **one tier** before it enters the roadmap. Direct implementation without tier assignment is not allowed.

### Tier definitions

| Tier | Name | Role |
|------|------|------|
| **1** | **Platform Foundation** | Core architecture, shared engines, standards — product cannot scale safely without these |
| **2** | **Business Features** | CRM modules that deliver direct business value |
| **3** | **User Experience** | UX polish, design system, interaction patterns |
| **4** | **Future Vision** | Long-term platform bets (AI, automation, multi-tenant, BI, etc.) |

### Tier 1 — Platform Foundation (examples)

Authentication · Authorization · Permission System · Universal DataTable · Universal Form · Universal Detail Page · Universal Import Engine · Universal Export Engine · Universal Background Job · Universal Notification Engine · Source Adapter Framework · Backup · Restore · Backup Policy · Scheduler · Audit · Health Monitoring · Storage Management · API Standards · Architecture Standards

**Rule:** Tier 1 gaps block **Tier 3** from taking priority over unfinished foundation work (unless product owner documents an explicit tier override — see ADR-023).

### Tier 2 — Business Features (examples)

Customer Management · Fair Management · Participation · Activities · Import · Export · Duplicate Detection · Merge Engine · Excel Mapping · Scraper Adaptors · TUYAP · IFM · F Istanbul · Reporting · Dashboard · Statistics

Business Phase P0/P1/P2 ([Product Vision](docs/PRODUCT_VISION.md)) applies **within Tier 2** for value ordering.

### Tier 3 — User Experience (examples)

KYROX Design System · Responsive Layout · Universal Wizard · Universal Cards · Universal Modal · Animations · Dark Theme · Accessibility · Keyboard Shortcuts · Empty State · Loading State · Progress Components · Typography · Spacing · Design Tokens

### Tier 4 — Future Vision (examples)

AI Assistant · Workflow Engine · Automation · Cloud Sync · Marketplace · Plugin System · REST Integrations · Webhook Platform · Multi Tenant · BI · Predictive Analytics · Universal Data Package (full maturity) · CRM Migration Toolkit

### Planning & implementation rules

1. **New idea** → assign **Tier** first → add to roadmap → then plan sprint.
2. **Sprint priority default:** Tier 1 → Tier 2 → Tier 3 → Tier 4.
3. **Product owner** may reprioritize; **tier changes** require documented rationale in roadmap / ADR note.

### Current delivery snapshot (indicative)

| Tier | Shipped (examples) | Planned / partial |
|------|-------------------|-------------------|
| **1** | Universal DataTable, Import Engine, Source Adapter Framework, Backup engine, API/list standards, Core auth integration | Universal Form, Backup Policy, Scheduler, Audit, Restore enablement, Export engine |
| **2** | Customers, Fairs, Participations, Contacts, Activities, Import/Merge wizard | CSV adapter, Emails, Reporting, Dashboard, fair scrapers (TUYAP/IFM/F Istanbul) |
| **3** | Navigation foundation, EmptyState, Modal, UniversalDataTable UX | Design System, Dark Theme, Universal Wizard, a11y |
| **4** | Universal Data Package MVP | AI platforms, Workflow, Multi-tenant, BI (see Product Vision) |

---

## System Administration & Business Continuity Roadmap (1–2 Years)

**Scope:** Architecture and product direction only. Implementation follows phased sprints after P0 customer-data work where appropriate.

**Canonical ADR:** [ADR-022 — System Administration & Business Continuity Roadmap](docs/DECISIONS.md)

### Admin → System — target navigation

```text
Admin
  System
    Dashboard                          (planned)
    Database Backups                     ✅ shipped (09.2.2 / 09.2.4)
    Backup Policies                      (planned)
    Backup Jobs                          (planned)
    Backup History                       (planned)
    Disaster Recovery                    (planned)
    Background Jobs                      (planned)
    Audit Logs                           (planned)
    Health Monitoring                    (planned)
    Scheduler                            (planned)
    Maintenance Mode                     (planned)
    Storage Management                   (planned)
    Environment Information              (planned)
    Cache Management                     (planned)
    License                              (planned)
    System Settings                      (planned)
```

### Business Continuity (conceptual area under System Administration)

Groups operational resilience capabilities:

| Module | Role | Status |
|--------|------|--------|
| **Database Backups** | Produce backup artifacts (`.dump`, `.sql`, `.zip`) | ✅ MVP |
| **Backup Policies** | Define *when*, *how often*, *how many*, *which format* | Planned |
| **Backup Jobs** | Execute policies and manual/ triggered runs | Planned |
| **Backup History** | Record every run: Completed / Failed / Skipped | Planned |
| **Backup Verification** | Post-backup integrity checks (beyond `pg_restore -l`) | Planned |
| **Disaster Recovery** | Runbooks, RTO/RPO targets, DR validation workflows | Planned |
| **Restore** | Controlled `.dump` restore (admin + dev); SQL/ZIP not restore targets | Foundation only |
| **Retention Policies** | Policy-scoped cleanup after successful backup | Planned |
| **Remote Backup** | Off-site copy of artifacts | Planned |
| **Cloud Backup** | S3, Azure Blob, GCS, NAS targets | Planned |

### Architecture principle — bounded contexts

These contexts remain **independently evolvable** (separate use cases, permissions, persistence where needed):

- Database Backup
- Backup Policy
- Backup History
- Backup Job
- Disaster Recovery
- Restore
- Universal Data Package

**Database Backup** produces files. **Backup Policy** decides schedule and rules. **Backup History** records outcomes. Do not merge policy logic into the backup engine.

### Backup Policy Engine (planned)

| Policy | Schedule | Retention | Notes |
|--------|----------|-----------|-------|
| **Daily** | Every day, configurable hour | **30** | Only if database changed (see change detection) |
| **Weekly** | Every Monday, configurable hour | **10** | When 11th weekly would be created, oldest weekly is removed |
| **Monthly** | First day of month, configurable hour | **12** or **Keep Forever** (configurable) | Long-term archive tier |

**Change detection (Daily):** Preferred rule — run backup only when `last_data_change > last_successful_backup`. Otherwise create **History** row: status **Skipped**, reason **No data changes**.

**Retention cleanup:** Runs after a **successful** backup. Policy-scoped deletion only. **Never** auto-delete the most recent successful backup globally.

### Backup History (planned fields)

Every execution recorded:

| Field | Description |
|-------|-------------|
| Status | Completed / Failed / Skipped |
| Skipped Reason | e.g. `No data changes` |
| Started At / Completed At / Duration | Timing |
| Policy | Daily / Weekly / Monthly / Manual |
| Trigger | See trigger types |
| Backup File | Artifact reference (if produced) |
| Change Detected | Boolean for daily smart skip |

### Trigger types (planned)

Manual · Scheduled · Before Import · Before Restore · Before Migration · Before Upgrade · Application Update · Schema Migration

### Backup formats — current and future

| Format | Purpose | Restore |
|--------|---------|---------|
| PostgreSQL Native (`.dump`) | Disaster recovery | Yes |
| PostgreSQL SQL (`.sql`) | Inspection / external tools | No |
| Universal Data Package (`.zip`) | Vendor-independent migration export | No |
| Cloud storage targets | S3, Azure Blob, GCS, NAS | N/A (delivery layer) |

**Universal Data Package** long-term target: `faircrm_package.zip` with `manifest.json`, entity JSON files, `metadata.json` — portable to MSSQL, MySQL, MariaDB, other CRMs. **Not a backup**; it is a **migration package**.

### Phased delivery (indicative)

| Phase | Focus | Indicative sprints |
|-------|--------|-------------------|
| **A — Foundation** | Backups workspace, formats, dev restore | ✅ 09.2.1 – 09.2.4 |
| **B — Operations** | Backup History, Restore enablement, verification UI, Before Import trigger | 10.x Admin |
| **C — Policy & retention** | Policy engine, scheduler integration, change detection, retention cleanup | 10.x – 11.x Admin |
| **D — DR & off-site** | Disaster Recovery workspace, remote/cloud copy | 11.x – 12.x Admin |
| **E — Platform admin** | Dashboard, jobs, audit, health, maintenance, storage, settings | 12.x+ Admin |

CSV Source Adapter (09.3) and Customer Emails (10) remain on the **customer-data P0 track**; Admin phases run in parallel when team capacity allows.

---

## Sprint Completion Log

| Sprint | Version | Completed |
|--------|---------|-----------|
| 01 — Customer Management | v0.2.0 | ✅ |
| 02 — Fair Management | v0.3.0 | ✅ |
| 03 — Customer Contacts | v0.4.0 | ✅ |
| 04 — Customer Activities | v0.5.0 | ✅ |
| 04.5 — UX Foundation | v0.5.1 | ✅ |
| 06 — Fair Participation | v0.7.0 | ✅ |
| 07 — Import Engine v1 | v0.6.0 | ✅ |
| 07 — Smart Import Wizard Phase 1 | v0.8.0 | ✅ |
| 07.1 — Smart Merge Viewer & Cleanup | v0.8.1 | ✅ |
| 08.1 — Detail Page Action Standard | v0.8.2 | ✅ |
| 08.0 — Universal Server-Side DataTable | v0.8.3 | ✅ |
| 09.0 — Data Integration Standard (docs) | v0.8.4 | ✅ |
| 09.1 — Data Integration Workspace | v0.9.0 | ✅ |
| 09.2 — Universal Source Adapter Framework | v0.9.1 | ✅ |
| 09.2.1 — Database Backup / Restore Standard | v0.9.2 | ✅ |
| 09.2.2 — Admin Database Backup Workspace | v0.9.3 | ✅ |
| 09.2.4 — Backup Format Options | v0.9.4 | ✅ |
| 09.2.5 — System Admin & BC Roadmap (docs) | — | ✅ |
| 09.2.6 — Tier-Based Product Delivery (docs) | — | ✅ |

---

## Update Protocol

When a sprint reaches Definition of Done ([PROJECT_CONSTITUTION.md § Sprint Workflow](PROJECT_CONSTITUTION.md#sprint-workflow)):

1. Move the sprint to **Completed** with its feature checklist.
2. Set the next sprint as **Current Sprint**.
3. Update **Current Version** and **Quality Gate** (test count, build status).
4. Add a row to **Sprint Completion Log** with the version bump.
5. Update [CHANGELOG.md](CHANGELOG.md) with the new version entry and delivered features.
6. Set **Last updated** to the completion date.

[PROJECT_STATUS.md](PROJECT_STATUS.md), [CHANGELOG.md](CHANGELOG.md), and [PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md) together form the single source of truth for project state and standards.

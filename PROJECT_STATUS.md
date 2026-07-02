# KYROX Fair CRM — Project Status

**Living status document** — updated automatically after every completed sprint.

| Field | Value |
|-------|-------|
| **Current Version** | v0.9.3 (Admin Database Backup Workspace) |
| **Last updated** | 2026-07-02 (Sprint 09.2.3 — Universal DataTable Sorting) |
| **Constitution** | [PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md) |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |
| **Product Vision** | [docs/PRODUCT_VISION.md](docs/PRODUCT_VISION.md) |

---

## Quality Gate

| Check | Status |
|-------|--------|
| Backend tests | **198 PASS** |
| Frontend build | **PASS** |
| Migration `0010_data_integration` | **APPLIED** (PostgreSQL) |
| Migration `0011_system_backups` | **APPLIED** (PostgreSQL) |
| Runtime verification (Sprint 09.2.2) | **PASS** — migration, reset-dev, Swagger, live API, live UI |
| Legacy UMCRM dev migration | **APPLIED** (115 fairs, 28,155 customers, 29,561 participations) |

---

## Completed

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

- Activity CRUD (create, read, update, soft delete)
- List activities by customer (paginated, sortable)
- Activity types: call, meeting, email, whatsapp, note, fair_visit, follow_up, other
- Activity status: open, completed, cancelled
- Activity source: manual (default), system, email_automation, whatsapp_integration, import, other
- Optional contact linkage with same-customer validation
- Follow-up date support
- Soft delete via `deleted_at` + `is_active`
- Swagger
- Customer detail page with Aktiviteler tab
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
| 09.3 | CSV Source Adapter | Planned |
| 10 | Customer Emails | Planned |
| 11 | Dashboard | Planned |
| 12 | Reporting | Planned |

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

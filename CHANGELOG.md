# Changelog

All notable Fair CRM releases are documented in this file.

Format: one version section per completed sprint milestone. Update this file after every completed sprint.

---

## Unreleased

### Width-responsive table standard (ADR-032 update)

- Default list engine: `UniversalDataTable` → `WidthResponsiveDataTable` (container width, column order = priority, child rows)
- Dual top+bottom pagination default via `ServerDataTableFrame` / `ServerDataTablePagination`
- Column squeezing / letter-break wrapping forbidden; `priority: "technical"` stays detail-only
- `ResponsiveDataTable` deprecated as thin adapter; all UniversalDataTable screens inherit the standard
- Docs: [docs/frontend/RESPONSIVE_UI_STANDARD.md](docs/frontend/RESPONSIVE_UI_STANDARD.md)

### Global Responsive UI Design System (ADR-032)

- Shared responsive standard for all Fair CRM screens (390 / 768 / 1024 / 1440)
- Form/filter 3/2/1, `FilterPanel`, `TruncatedText`, `TechnicalDetails`, modal bottom-sheet
- List tables: width-responsive engine (see above)
- [docs/frontend/RESPONSIVE_UI_STANDARD.md](docs/frontend/RESPONSIVE_UI_STANDARD.md)

### Import Job Permanent Delete

- `DELETE /api/v1/data-integration/imports/{batch_id}` — hard delete batch, rows, jobs, stored Excel bytes
- Active analyze/apply job or `analyzing`/`applying` status blocks delete (409)
- Import list **Sil** button with confirmation dialog + success toast

### Import Job Resume Flow + Decision Bulk Actions

- Upload sonrası Import İşleri listesine yönlendirme
- **Devam Et** — status-aware setup/decision resume (`/imports/continue/:id`)
- Bulk preview: `POST .../bulk-actions/preview` (veri değiştirmez)
- Bulk apply job: `POST .../bulk-actions/apply` (202, background)
- Batch apply/bulk lock (409); idempotent bulk (skip rows with decision)
- [docs/IMPORT_RESUME_BULK_COMPLETION.md](docs/IMPORT_RESUME_BULK_COMPLETION.md)

### Company Name Matching Stabilization

- Turkish-aware normalization + legal suffix / abbreviation handling
- Token-based scoring with confidence bands (70 / 85 / 95)
- Match explanations stored on import rows (`_match_explanation`)
- [docs/COMPANY_NAME_MATCHING_COMPLETION.md](docs/COMPANY_NAME_MATCHING_COMPLETION.md)

### Universal Excel Import — Column Mapping Grid + Analysis Queue

- Excel preview + per-column mapping grid (dropdown per column)
- Wizard setup: upload → sheet → header → mapping grid → Import Jobs list
- Batch lifecycle statuses (`mapping_completed`, `analysis_queued`, `analyzing`, `decision_required`, …)
- Background analyze via `POST .../analyze-job` (FastAPI BackgroundTasks)
- Organization-level analyze concurrency lock (409 on conflict)
- Migration `0015_import_batch_lifecycle`
- [docs/IMPORT_MAPPING_GRID_COMPLETION.md](docs/IMPORT_MAPPING_GRID_COMPLETION.md)

### Development runtime (Sprint — Dev Auto Start Standard v1) — MERGE APPROVED

- `docker-compose.yml` — `restart: unless-stopped` on PostgreSQL
- `scripts/dev/dev-lib.ps1` — shared Docker/runtime helpers
- `scripts/dev/dev-start.ps1` — idempotent auto-start (Docker + backend + frontend)
- `scripts/dev/dev-stop.ps1` — stop runtime processes; optional `-StopInfra`
- `scripts/dev/reset-dev.ps1` — refactored to use `dev-lib.ps1` (force reset unchanged)
- `scripts/dev/verify-dev-auto-start.ps1` — automated validation suite
- Windows reboot manual verification: **PASS** (2026-07-02)
- [docs/DEV_RUNTIME.md](docs/DEV_RUNTIME.md) — auto-start workflow documented
- [docs/DEV_AUTO_START_COMPLETION.md](docs/DEV_AUTO_START_COMPLETION.md) — validation results + sign-off

### Shipped (implementation)

- Customer hard-delete cascade safety (ADR-020) — migrations `0012` / `0013`; archive preserved, DR hard delete cascades
- **Backup format options (Sprint 09.2.4 / ADR-021)** — Admin create modal: `.dump` (DR), `.sql` (plain export), Universal Data Package `.zip` (MVP)
- Migration `0014_backup_format_options` — `backup_format`, `manifest_json` on `system_backups`
- `UniversalDataPackageService` — vendor-independent JSON + manifest ZIP export (not restore)
- Restore remains `.dump`-only; SQL and data package are export/migration formats
- **Universal Server-Side DataTable Sorting Rule (ADR-019)** — mandatory sortable data columns except Actions
- `UniversalDataTable` component — column `{ key, title, sortable: true }` auto-manages sort headers
- Canonical API sort params: `sort_by` + `sort_order` (legacy `sort`/`direction`/`sort_dir` aliases retained)
- All list screens migrated: Fairs, Customers, Participations, Contacts, Activities, Imports, Admin Backups
- Backend whitelist tests extended; invalid sort fields fall back safely (no 400)
- URL sort state on Fairs, Customers, Imports, Backups list pages

### Architecture (documentation only — Sprint 09.2.5)

- **ADR-022** — System Administration & Business Continuity Roadmap (1–2 years)
- Official Admin → System navigation target; Business Continuity conceptual model
- Backup Policy Engine design (Daily / Weekly / Monthly, change detection, retention)
- Backup History, trigger types, bounded contexts (Backup vs Policy vs History vs DR vs Restore vs UDP)
- Future: cloud/remote backup (S3, Azure Blob, GCS, NAS), DR workspace, platform admin modules
- Updated: `PROJECT_STATUS.md`, `PROJECT_CONSTITUTION.md`, `docs/PRODUCT_VISION.md`

### Product management (documentation only — Sprint 09.2.6)

- **ADR-023** — Tier-Based Product Delivery Strategy (Tier 1–4)
- Planning rule: Tier assignment before roadmap; default priority Tier 1 → 2 → 3 → 4
- Tier 1 gate: UX (Tier 3) does not outrank open foundation without documented override
- Updated: `PROJECT_STATUS.md`, `PROJECT_CONSTITUTION.md`, `docs/PRODUCT_VISION.md`

## v0.9.3 — Admin Database Backup Workspace

- **System Administration** module foundation (`system_admin`) — first production-grade admin capability
- Shared backup engine (`app/shared/database_backup`) — used by dev PowerShell scripts and Admin API (no duplicated dump logic)
- Migration `0011_system_backups` — backup metadata (`system_backups` table)
- Admin API `/api/v1/admin/backups` — create (202 + background job), list, get, download
- Restore foundation — `RestoreService`, disabled endpoint (`501`), UI Restore button disabled
- Frontend **Admin → System → Database Backups** at `/admin/system/backups` with live progress polling
- Permissions: `fair_crm.admin.backups.create`, `.read`, `.download`
- Path traversal protection on download; files served from gitignored `backups/` only
- ADR-018 + runtime DoD: migration, reset-dev, Swagger, live API, live UI
- Backend tests (185) PASS; frontend build PASS

## v0.9.2 — Database Backup / Restore Standard (dev utility)

- `scripts/dev/backup-db.ps1` — PostgreSQL custom-format backup (`.dump`) with post-backup `pg_restore -l` verification
- `scripts/dev/restore-db.ps1` — safe restore with `-WhatIf` / `-DryRun` and database-name confirmation
- `scripts/dev/list-backups.ps1` — list local backups with timestamp and size
- Reads `DATABASE_URL` from `backend/.env`; stores dumps under gitignored `backups/`
- PROJECT_CONSTITUTION.md — Development Utilities / Database Safety section

## v0.9.1 — Universal Source Adapter Framework

- **SourceAdapter** protocol and **SourceAdapterRegistry** — pluggable data sources without Import Engine changes
- **ExcelSourceAdapter** migrated to formal adapter lifecycle (Connect → Read → Normalize → Preview)
- Upload and sheet selection resolve adapters via registry
- Background apply job fix — runs after DB commit via FastAPI `BackgroundTasks`
- ADR-017 + [docs/import/SOURCE_ADAPTER_FRAMEWORK.md](docs/import/SOURCE_ADAPTER_FRAMEWORK.md)
- Backend tests (180) PASS

## v0.9.0 — Data Integration Workspace & Universal Import Engine

- **Data Integration module** (`data_integration`) — Universal Import Engine with Excel adapter
- API `/api/v1/data-integration/imports/*` (legacy `/imports/*` retained)
- Excel header modes: İlk satır başlık / Başlık yok / Başlık satırını ben seçeceğim
- Sheet selection, import batch list, background apply jobs with progress polling
- Migration `0010_data_integration` — jobs, templates, batch header fields
- Frontend **Veri Entegrasyonu** at `/data-integration` (Import İşleri, Yeni Import, Jobs, Reports)
- Merge decisions extended: `participation_only`, `manual_review`
- Runtime DoD: migration `0010`, dev reset, Swagger verification, live API script (4 scenarios)
- Backend tests (176) and frontend build PASS

---

## v0.8.3 — Universal Server-Side DataTable Standard

- Shared list query contract: `page`, `pageSize`, `search`, `sort`, `direction`, entity filters (legacy aliases retained)
- Shared list response: nested `pagination`, `sorting`, `filters` on all list endpoints
- Server-side search/sort/filter extended to Contacts, Activities, Participations, Import rows
- Fair Participants list optimized for 29k+ participation records (server-side only)
- Migration `0009_list_indexes` for customer, fair, activity, participation list fields
- Frontend `useServerDataTable` hook with URL state sync (refresh, back, forward, shareable links)
- Enhanced `DataTable` with sortable column headers (ASC → DESC → NONE cycle)
- Migrated: Customers, Fairs, Customer Detail tabs, Fair Participants, Import Wizard preview rows
- ADR-015 documented; List Screen Definition of Done added to PROJECT_CONSTITUTION.md
- Backend tests (173) and frontend build PASS

---

## v0.8.2 — Detail Page Action Standard

- `PageHeader` extended with typed `actions` array API (`primary` | `secondary` | `danger`) and breadcrumb back links
- Customer Detail action bar: Düzenle, İletişim Kişisi Ekle, Fuara Ekle, Yeni Aktivite, Arşivle — available from any tab without returning to list
- Fair Detail action bar: Düzenle, Katılımcı Firma Ekle, Katılımcıları İçe Aktar, Yeni Aktivite (disabled pending fair-scoped activity API), Arşivle
- Edit/archive modals and forms wired directly on Detail pages; Import Wizard opens from Fair Detail with fair preselected
- ADR-014 — Detail Page Action Standard documented in [docs/DECISIONS.md](docs/DECISIONS.md)
- Frontend build and browser verification PASS

---

## v0.8.1 — Smart Merge Viewer & Cleanup

- Merge diff viewer: field-level CRM vs Import preview with entity grouping (Customer, Participation, Contact)
- Backend `merge_preview` on import row list/decision responses with Turkish summary lines
- Preview UX: filters, company search, sort by confidence/company/status
- Contact import apply verified end-to-end (API + live script)
- Legacy `POST /api/v1/imports/customers/upload` deprecated for removal in v0.9.0
- Removed unused frontend `ImportsPage.tsx`
- `scripts/verify_wizard_imports_live.py` extended with merge preview + contact scenarios
- Dev runtime reset script: `scripts/dev/reset-dev.ps1` + [docs/DEV_RUNTIME.md](docs/DEV_RUNTIME.md)

---

## v0.8.0 — Smart Import Wizard Phase 1

- Smart Import Wizard: 9-step UI at `/imports` with fair context (ADR-012)
- `POST /api/v1/imports/upload` — raw Excel preview without CRM writes
- `PATCH /api/v1/imports/{batch_id}/column-mapping` — manual mapping (headerless Excel supported)
- `POST /api/v1/imports/{batch_id}/analyze` — separate analyze step
- `PATCH /api/v1/imports/{batch_id}/rows/bulk-decision` — bulk merge decisions
- Import batch `fair_id` required for wizard flow; migration `0008_import_wizard`
- Two-level duplicate detection: Customer + Participation in selected Fair
- Apply creates/updates `CustomerFairParticipation` with hall/stand/notes on participation
- Fair Detail → Katılımcıları İçe Aktar entry route `/imports/fair/{id}`
- `fair_name` removed from supported mapping fields
- Backend tests (18 wizard scenarios) + legacy import tests retained
- Frontend build verified

---

## v0.7.0 — Customer Fair Participation

- `CustomerFairParticipation` join entity (`crm_customer_fair_participations`) linking customers and fairs
- Hall, stand, participation status, notes, primary contact, visited_at on participation (import-ready)
- Participation statuses: planned, exhibitor, visited, contacted, follow_up_required, not_interested, customer, other
- Unique active customer + fair; soft delete; recreate allowed after delete
- Primary contact must belong to the same customer
- Create blocked for archived customer or fair
- API: `GET /customers/{id}/fair-participations`, `GET /fairs/{id}/participants`, CRUD `/fair-participations/{id}`
- Customer detail **Katıldığı Fuarlar** tab (add, edit, delete)
- Fair detail page with **Katılımcı Firmalar** tab; company name links to customer detail
- Turkish UI labels and status translations
- Backend tests and `scripts/verify_participations_live.py`

---

## v0.6.0 — Import Engine v1

- Import batch and import row persistence with preview/apply workflow
- Excel (.xlsx) upload with Turkish column alias mapping (Firma Adı, E-posta, …)
- Company name normalization for duplicate detection (Turkish chars, legal suffix removal)
- Row validation (required company_name, multi-email, website URL)
- Duplicate detection within batch and against existing customers (exact + fuzzy via SequenceMatcher)
- Per-row merge decisions: create_new, update_existing, skip (no blind auto-merge)
- Apply import: create/update customers, merge empty fields, merge multi-email, contact create/update
- Import activities (type note, source import) on create/update
- API: `POST /imports/customers/upload`, batch/rows GET, decision PATCH, apply POST
- Frontend **İçe Aktarma** page at `/imports` with upload panel, preview summary, rows table, apply confirm
- Backend tests and live verification script (`scripts/verify_imports_live.py`)

---

## v0.5.1 — UX & Navigation Foundation

- Sidebar + top bar application layout with breadcrumb navigation
- Reusable UI component library under `frontend/src/components/ui/`
- Customer detail page unified tab experience
- Activity timeline with badges, date emphasis, and hover cards
- Standardized empty states, loading skeletons, and confirm dialogs (replacing `window.confirm`)
- Consistent table, form, badge, and color styling across customers, contacts, activities, and fairs
- Responsive sidebar toggle for tablet/narrow screens
- Search placeholder standardization

---

## v0.5.0 — Customer Activities

- Activity CRUD (create, read, update, soft delete)
- List activities by customer with pagination and sorting
- Activity types: call, meeting, email, whatsapp, note, fair_visit, follow_up, other
- Activity status: open, completed, cancelled
- Activity source enum with default `manual` (system/automation values ready for future integrations)
- Optional contact linkage with same-customer validation
- Follow-up date support
- Customer detail page **Aktiviteler** tab with timeline list and add/edit dialog
- Turkish frontend labels for types, status, and source
- Backend tests and live API verification script

---

## v0.4.1 — Multi-Email Support (Customer & Contact)

- Semicolon-separated multi-email in existing `email` string field
- Comma and whitespace normalization on create/update
- Duplicate email deduplication
- Per-address validation with invalid address in error detail
- Turkish frontend placeholder and validation messages

---

## v0.4.0 — Customer Contacts

- Contact CRUD (create, read, update, soft delete)
- List contacts by customer
- Primary contact rule (one `is_primary` per customer)
- Full name computed in API response (not stored in database)
- Customer detail page with İletişim Kişileri tab
- Turkish frontend labels and validation messages
- Backend tests

---

## v0.1.0 — Customer Management Foundation

Initial customer module foundation: domain model, backend structure, Core integration, and Phase 1 design.

---

## v0.2.0 — Customer Management Production Ready

- CRUD
- Archive
- Restore
- Pagination
- Sorting

---

## v0.3.0 — Fair Management

- CRUD
- Archive
- Restore
- Pagination
- Search
- Sorting

---

## Update Protocol

When a sprint completes:

1. Add a new version section below the header (above older entries).
2. List delivered features as bullet points.
3. Bump version according to sprint scope (minor version per major module sprint unless otherwise decided).
4. Update [PROJECT_STATUS.md](PROJECT_STATUS.md) to match the new current version.

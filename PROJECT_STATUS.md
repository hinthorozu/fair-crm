# KYROX Fair CRM — Project Status

**Living status document** — updated automatically after every completed sprint.

| Field | Value |
|-------|-------|
| **Current Version** | v0.8.1 |
| **Last updated** | 2026-07-01 |
| **Constitution** | [PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md) |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

---

## Quality Gate

| Check | Status |
|-------|--------|
| Backend tests | **171 PASS** |
| Frontend build | **PASS** |

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

---

## Current Sprint

**Sprint 05 — Customer Phones**

Status: Planned — pending start

---

## Upcoming

| Sprint | Module |
|--------|--------|
| Sprint 05 | Customer Phones |
| Sprint 08 | Customer Emails |
| Sprint 09 | Dashboard |
| Sprint 10 | Reporting |

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

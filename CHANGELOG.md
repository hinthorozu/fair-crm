# Changelog

All notable Fair CRM releases are documented in this file.

Format: one version section per completed sprint milestone. Update this file after every completed sprint.

---

## Unreleased

- Legacy UMCRM migration engine: canonical JSON → KYROX CRM (dev-only)
- Scripts: `reset_fair_crm_dev_domain.py`, `migrate_umcrm_to_kyrox.py`
- Full dev import verified: 115 fairs, 28,155 customers, 29,561 participations
- Documentation: [docs/LEGACY_UMCRM_MIGRATION.md](docs/LEGACY_UMCRM_MIGRATION.md)

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

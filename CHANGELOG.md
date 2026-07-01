# Changelog

All notable Fair CRM releases are documented in this file.

Format: one version section per completed sprint milestone. Update this file after every completed sprint.

---

## Unreleased

_No unreleased changes._

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

# Changelog

All notable Fair CRM releases are documented in this file.

Format: one version section per completed sprint milestone. Update this file after every completed sprint.

---

## Unreleased

### Documentation

- Added Activity Timeline architectural principle.
- Documented that future automated Customer/Contact communications, including sent emails, must create Activity records.
- Added Sprint 04 Customer Activities planning notes.

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

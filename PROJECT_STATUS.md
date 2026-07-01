# KYROX Fair CRM — Project Status

**Living status document** — updated automatically after every completed sprint.

| Field | Value |
|-------|-------|
| **Current Version** | v0.4.1 |
| **Last updated** | 2026-07-01 |
| **Constitution** | [PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md) |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

---

## Quality Gate

| Check | Status |
|-------|--------|
| Backend tests | **92 PASS** |
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

---

## Current Sprint

**Sprint 04 — Customer Activities**

Status: Planned — pending start

---

## Planned — Sprint 04: Customer Activities

Planned scope:

- Customer Activity Timeline
- Manual activity creation
- Activity types such as Call, Meeting, Email, WhatsApp, Note, Fair Visit, Follow-up
- Optional Contact linkage
- Follow-up date support
- Automatic activity generation for future system actions
- Sent email history integration
- Future WhatsApp integration

---

## Upcoming

| Sprint | Module |
|--------|--------|
| Sprint 05 | Customer Phones |
| Sprint 06 | Customer Emails |
| Sprint 07 | Fair Participations |
| Sprint 08 | Import Engine |
| Sprint 09 | Duplicate Detection |
| Sprint 10 | Merge Decision |
| Sprint 11 | Dashboard |
| Sprint 12 | Reporting |

---

## Sprint Completion Log

| Sprint | Version | Completed |
|--------|---------|-----------|
| 01 — Customer Management | v0.2.0 | ✅ |
| 02 — Fair Management | v0.3.0 | ✅ |
| 03 — Customer Contacts | v0.4.0 | ✅ |
| 04 — Customer Activities | — | — |

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

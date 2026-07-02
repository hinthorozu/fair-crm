# KYROX Fair CRM — Project Constitution

**Status:** Canonical development constitution  
**Scope:** `fair-crm` repository only  
**Current version:** v0.3.0

This document is the official development constitution of the KYROX Fair CRM project. All future development in `fair-crm` must follow these rules. When in doubt, this file takes precedence over informal notes or chat history.

**Change policy:** [PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md) should only change when project standards evolve — not on every sprint.

---

## Single Source of Truth

These files are the project's **single source of truth**:

| Document | Role |
|----------|------|
| [PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md) | Development standards and workflow (this file) |
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | Living sprint and quality status |
| [CHANGELOG.md](CHANGELOG.md) | Version history and delivered features |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture Decision Records |
| [docs/PRODUCT_VISION.md](docs/PRODUCT_VISION.md) | Long-term product direction and business workflow |

### Mandatory Rule — Before Starting Any New Sprint

1. Read [PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md)
2. Read [PROJECT_STATUS.md](PROJECT_STATUS.md)
3. Read [CHANGELOG.md](CHANGELOG.md)
4. Read [docs/PRODUCT_VISION.md](docs/PRODUCT_VISION.md)
5. Read [docs/DECISIONS.md](docs/DECISIONS.md) for ADRs relevant to the sprint

No sprint work begins until these documents have been read and understood.

### Supporting Documents

| Document | Role |
|----------|------|
| [README.md](README.md) | Setup, quick start, and integration guide |
| [ROADMAP.md](ROADMAP.md) | Milestone planning |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture Decision Records |
| [docs/PRODUCT_VISION.md](docs/PRODUCT_VISION.md) | Long-term product direction (see also canonical table above) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Detailed architecture reference |

---

## Project Vision

FAIR CRM is the first product on the KYROX platform. It manages fair and exhibition relationships: customers, contacts, fairs, participations, imported exhibitor data, duplicate detection, merge decisions, and CRM follow-up workflows.

**Long-term direction** is documented in [docs/PRODUCT_VISION.md](docs/PRODUCT_VISION.md): a **Customer Data Platform** that acquires, enriches, verifies, and improves customer information — with mandatory human approval before CRM writes.

### Product Vision Principles (canonical)

1. **Business Workflow First** — Development priorities follow the official business phases (Customer Acquisition → Customer Enrichment → Fair Discovery) and business-value ordering (P0 / P1 / P2) defined in [docs/PRODUCT_VISION.md](docs/PRODUCT_VISION.md). Technical complexity alone does not set sprint priority.
2. **Preview First** — No import or external data is written directly to CRM (extends ADR-005, ADR-016).
3. **Human Approval Required** — External data, enrichment, verification results, and AI suggestions never update CRM automatically.
4. **Platform Thinking** — Universal Import, Company Intelligence, Data Quality, AI, and Integration remain independent platforms with clear boundaries.
5. **Compass over itinerary** — Roadmaps and sprint scope may change; architectural principles and product vision remain stable (see Product Vision team motto).

### Purpose

Fair data is usually fragmented across Excel files, scraped exhibitor lists, manual notes, contact records, and repeated company names. FAIR CRM makes it easy to:

- Import exhibitor and customer data safely
- Detect and resolve duplicates
- Merge incomplete records with explicit decisions
- Track customers across multiple fairs
- Manage contacts and communication details
- Prepare reports and follow-up lists

### Product Principles

1. Do not blindly import duplicate records.
2. Always preview imported data before writing final CRM records.
3. Normalize customer names for matching, but preserve original display names.
4. Keep platform concerns in **KYROX Core** — never reimplement auth, RBAC, audit, settings, jobs, or notifications in Fair CRM.
5. Backend, API, and database use **English**; frontend user-facing text uses **Turkish**.
6. Prefer clear, explicit workflows over hidden automation.

---

## Project Scope

### In Scope (`fair-crm` only)

- CRM domain modules: customers, contacts, phones, emails, fairs, participations, import, duplicate detection, merge decisions, dashboard, reporting
- Product FastAPI service, product PostgreSQL database (`crm_*` tables)
- Product frontend (React + TypeScript)
- Integration with KYROX Core via public HTTP APIs (auth validation, permission check, audit write)
- Product tests, migrations, Swagger, and Turkish UI

### Out of Scope

| Area | Owner | Rule |
|------|-------|------|
| Authentication, RBAC, orgs, audit platform, settings, jobs, notifications | `kyrox-core` | Integrate via API — do not modify from Fair CRM sprints |
| Platform roadmap and milestones | `kyrox-platform` | Do not modify from Fair CRM sprints |
| Legacy `fuar-crm` architecture | Reference only | May inform fields and workflows; not target architecture (ADR-004) |

### Repository Boundaries

| Repository | Purpose | Fair CRM may modify? |
|------------|---------|----------------------|
| `kyrox-platform` | Roadmap, milestones, project management | No |
| `kyrox-core` | Platform service | No |
| `fair-crm` | Product service — CRM domain only | **Yes** |

### Language

- Backend code, database schema, API paths, query params, permission codes: **English**
- Frontend labels, user messages, confirmations, empty states: **Turkish**

---

## Architecture Rules

FAIR CRM is an **independent FastAPI service** with its own PostgreSQL database. It integrates with KYROX Core **only through public HTTP APIs**.

```text
Client → KYROX Core (login, orgs, RBAC)
Client → FAIR CRM (customers, fairs, …) with JWT + X-Organization-Id
FAIR CRM → KYROX Core (permission check, audit write, settings)
```

### Hard Rules

1. **No Core Python imports** — Do not import `kyrox-core` modules (`app.modules.*`, `app.db.*`, etc.).
2. **Separate databases** — Fair CRM uses its own `DATABASE_URL`. Do not share SQLAlchemy sessions or connection pools with Core.
3. **No cross-repo foreign keys** — `organization_id` is a logical tenant key from Core, not a DB FK to Core tables.
4. **No Core routes in Fair CRM** — Auth, org management, and platform services are served by Core only.
5. **Modular monolith internally** — One Fair CRM codebase, one process, layered modules under `backend/app/modules/`.
6. **Layered modules** — Each product module follows: `domain → application → infrastructure → api`.
7. **Inward dependencies** — `api → application → domain`; `infrastructure → domain`; Core integration via `integrations/kyrox_core/` HTTP adapters only.
8. **Org scoping mandatory** — Every product use case enforces `organization_id` from validated auth context, never from an unvalidated request body alone.
9. **Table naming** — Product tables use the `crm_` prefix in the `fair_crm` database.
10. **Dev bypass is local only** — `FAIR_CRM_DEV_BYPASS_CORE` and frontend dev-bypass headers are forbidden in production builds.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/INTEGRATION_WITH_CORE.md](docs/INTEGRATION_WITH_CORE.md).

---

## ADR-009 Reference

**ADR-009 — Evaluate platform reusability before every new feature**

Status: Accepted — see [docs/DECISIONS.md](docs/DECISIONS.md)

Before implementing any new Fair CRM business feature, evaluate whether the capability is **generic platform infrastructure** reusable across KYROX products.

### Rules

1. **Evaluate first** — During Phase 1 design (before Phase 2 code), ask: could another product (not only Fair CRM) need this without CRM-specific semantics?
2. **If platform-generic** — Stop Fair CRM implementation. Document the need and **propose it for KYROX Core** first. Wait for approval and Core delivery (or an explicit decision to defer) before continuing in `fair-crm`.
3. **If product-specific** — Proceed in `fair-crm`. CRM domain logic, fair/exhibitor workflows, and Fair CRM permission semantics stay here.
4. **Integrate via Core APIs** — When Core already provides the capability, consume it through public APIs; do not reimplement or duplicate in `fair-crm`.

### Examples

| Capability | Owner |
|------------|-------|
| Auth, RBAC, audit write, settings, jobs, notifications | KYROX Core |
| Customer, import pipeline, duplicate merge, fair participation | Fair CRM |
| New generic permission-check pattern, file storage, webhooks | Evaluate → likely Core |

Report platform needs in design docs and track in `kyrox-platform` before changing `kyrox-core`.

**ADR-009 is mandatory at the start of every sprint Phase 1.**

---

## Backend Standards

### Stack

- Python 3.12+, FastAPI, SQLAlchemy, Alembic, PostgreSQL
- Tests: pytest with `TestClient` for API layer

### Layer Responsibilities

| Layer | Rules |
|-------|-------|
| **domain** | Pure business logic. No FastAPI, SQLAlchemy, or HTTP imports. |
| **application** | Orchestrates use cases. Depends on domain ports. Calls Core via injected authorization/audit ports. |
| **infrastructure** | Implements repositories. Org-scoped queries mandatory. |
| **api** | Thin HTTP layer. Maps request/response schemas. Delegates to use cases. |

### Naming and Conventions

- Use cases: `<Verb><Entity>UseCase` (e.g. `CreateCustomerUseCase`)
- Commands/queries: `<Verb><Entity>Command` / `<Verb><Entity>Query`
- Repository port: `<Entity>Repository` in domain; `SqlAlchemy<Entity>Repository` in infrastructure
- Permission codes: `fair_crm.<module>.<action>` (e.g. `fair_crm.customers.read`)
- Audit actions: `fair_crm.<entity>.<past_tense>` (e.g. `fair_crm.customer.archived`)

### Migrations

- Product migrations live in `backend/alembic/versions/`
- Create `crm_*` tables only — never Core platform tables
- Run `alembic upgrade head` from repository root

### Shared Utilities

- Pagination: `backend/app/core/pagination.py`
- Pagination OpenAPI fields: `backend/app/api/schemas/pagination.py`
- Core HTTP adapters: `backend/app/integrations/kyrox_core/`

### Core Integration

- Permissions registered in Core by platform change; Fair CRM consumes via authorization check API
- Audit writes are **best-effort** — mutation success must not fail if Core audit is unavailable

---

## Frontend Standards

### Stack and Structure

- **Stack:** React + TypeScript + Vite
- **Labels:** Turkish strings in `frontend/src/labels/` (per-module label files encouraged)
- **API client:** `frontend/src/api/client.ts` — all requests use `buildApiHeaders()` from `config.ts`
- **Types:** `frontend/src/types/` — one file per domain entity
- **Pages:** `frontend/src/pages/` — route-level containers
- **Components:** `frontend/src/components/` — reusable UI (list, form, pagination bar)

### Conventions

1. **No English in UI** — All visible text, confirmations, errors, and empty states are Turkish.
2. **Centralized API modules** — One file per resource under `frontend/src/api/` (e.g. `customers.ts`, `fairs.ts`).
3. **Paginated lists** — Use shared `PaginationBar` and `normalizePaginatedResponse()`.
4. **Archive/restore UX** — Confirm before archive/restore; show success/error messages; visually distinguish archived rows.
5. **Dev bypass automatic in dev** — `config.ts` attaches bypass headers during local development; production builds never send them.
6. **Error handling** — Use `ApiError` and module-specific fallback messages from label files.

---

## Module Standard

Every new product module must follow the same delivery pattern established by **customers** (Sprint 01) and **fairs** (Sprint 02).

### Directory Layout

```text
backend/app/modules/<module>/
├── domain/           # Entities, value objects, ports, domain exceptions
├── application/      # Use cases, commands, queries, mappers
├── infrastructure/   # SQLAlchemy models, repositories, mappers
└── api/              # FastAPI routes, schemas, dependencies

backend/tests/modules/<module>/   # Domain, application, infrastructure, API tests
backend/alembic/versions/         # crm_<module> migration

frontend/src/
├── types/<module>.ts
├── api/<module>s.ts              # or singular as appropriate
├── labels/<module>Labels.ts
├── components/<Module>List.tsx
├── components/<Module>Form.tsx
└── pages/<Module>sPage.tsx
```

### Module Definition of Done

| Deliverable | Required |
|-------------|----------|
| Domain entity with org scoping | Yes |
| CRUD use cases | Yes |
| Alembic migration (`crm_*` table) | Yes |
| API routes under `/api/v1/` | Yes |
| Permissions (`fair_crm.<module>.*`) | Yes |
| Pagination on list endpoint | Yes |
| Search and sorting (where applicable) | Yes |
| Archive and restore (archivable entities) | Yes |
| Swagger documentation | Yes |
| Backend tests (all layers) | Yes |
| Turkish frontend page | Yes |
| Router registration in `App.tsx` | Yes |

### Cross-Module Rules

- Modules communicate via application services — not cross-infrastructure imports
- Shared product primitives go under `backend/app/shared/` if needed
- Child entities (contacts, phones, emails) belong to their parent customer scope
- Reuse pagination, archive/restore, API, and frontend patterns — do not invent parallel conventions

---

## Pagination Standard

All list endpoints and list UIs must follow this standard.

### Backend

| Parameter | Default | Constraints |
|-----------|---------|-------------|
| `page` | `1` | ≥ 1, 1-based |
| `page_size` | `25` | 1–100 |
| `sort_by` | module-specific (e.g. `created_at`) | Whitelist allowed columns in repository |
| `sort_order` | `desc` | `asc` or `desc` (aliases: `sort_dir`, `direction`) |

**Response shape** (snake_case):

```json
{
  "items": [],
  "page": 1,
  "page_size": 25,
  "total": 0,
  "total_pages": 0
}
```

Use `normalize_page_params()` and `build_paginated_meta()` from `app.core.pagination`. List response schemas inherit `PaginationMeta`.

### Frontend

| Constant | Value |
|----------|-------|
| `DEFAULT_PAGE` | `1` |
| `DEFAULT_PAGE_SIZE` | `25` |
| `PAGE_SIZE_OPTIONS` | `10, 25, 50, 100` |

Use `normalizePaginatedResponse()` for all list API calls. Render pagination with shared `PaginationBar`.

### Search and Filters

- `search` — free-text query param on list endpoints where applicable
- Domain-specific filters (e.g. `status`, `customer_type`) are optional query params
- Filters combine with pagination; total reflects filtered count

---

## Archive & Restore Standard

Archive is a **soft delete** with status preservation for restore. This pattern is mandatory for all archivable aggregates.

### Domain Rules

1. **Archive** sets `status = archived`, `deleted_at = now`, and stores prior status in `archived_from_status` (when applicable).
2. **Restore** clears `deleted_at`, restores `status` from `archived_from_status`, and clears `archived_from_status`.
3. **Default restore status** — If `archived_from_status` is missing, use module default (`active` for customers, `planned` for fairs).
4. **Immutability** — Archived entities reject update mutations.
5. **Restore guard** — Restoring a non-archived entity returns `400` with a clear domain message.

### API Endpoints

| Action | Method | Path | Permission |
|--------|--------|------|------------|
| Archive | `DELETE` | `/api/v1/<resource>/{id}` | `fair_crm.<module>.archive` |
| Restore | `POST` | `/api/v1/<resource>/{id}/restore` | `fair_crm.<module>.archive` |

Both return the full resource response body (not 204).

### List Behavior

| Query | Behavior |
|-------|----------|
| Default list (no status filter) | Returns all records including archived |
| `status=<active_status>` | Excludes archived records |
| `status=archived` | Returns archived records only |
| `include_archived=true` (legacy compat) | Treated as archived filter when no status given |

### Frontend

- Archive button with Turkish confirmation dialog
- Restore button visible only for archived rows
- Archived rows styled distinctly (e.g. `row-archived` class)
- Status filter includes `archived` option

---

## API Standard

### Base URL and Versioning

- Fair CRM base: `/api/v1`
- Health: `GET /health` (unauthenticated)

### Authentication Headers

Every org-scoped route requires:

```http
Authorization: Bearer <access_token>
X-Organization-Id: <organization_uuid>
```

### HTTP Methods

| Operation | Method | Path pattern |
|-----------|--------|--------------|
| Create | `POST` | `/<resources>` |
| List | `GET` | `/<resources>` |
| Get by id | `GET` | `/<resources>/{id}` |
| Update | `PATCH` | `/<resources>/{id}` |
| Archive | `DELETE` | `/<resources>/{id}` |
| Restore | `POST` | `/<resources>/{id}/restore` |

### Response and Error Conventions

- Create returns `201` with resource body
- Update/archive/restore return `200` with resource body
- Not found (wrong org or missing id): `404` with `{ "detail": "..." }`
- Domain validation errors: `400` with `{ "detail": "..." }`
- Permission denied: `403`
- Unauthenticated: `401`

### OpenAPI / Swagger

- All routes documented in FastAPI with `response_model`, `tags`, and error response schemas
- Swagger UI at `/docs` when service is running

### Field Naming

- JSON request/response bodies use **snake_case**
- UUIDs as strings
- Datetimes as ISO 8601 with timezone

---

## Testing Standard

### Layer Coverage

| Layer | Approach |
|-------|----------|
| Domain | Unit tests; no DB, no HTTP |
| Application | Unit tests with fake repositories and fake Core ports |
| Infrastructure | Integration tests against product DB |
| API | `TestClient`; org isolation and permission paths mandatory |

### Required Test Cases per Module

Every CRUD module must include tests for:

- Create, read, update
- List with default pagination
- Search and sort (where applicable)
- Status filters
- Archive and restore (including wrong-org 404, restore-non-archived 400)
- Archived visibility in default list vs filtered list

### Running Tests

From repository root:

```bash
python scripts/quality_check.py
```

Or from `backend/`:

```bash
python -m pytest -q
```

Quality check runs: Python compile, FastAPI import, and full pytest suite.

### Frontend

- `npm run build` must pass before sprint completion
- Manual smoke test of list, create, edit, archive, restore in Turkish UI

---

## Runtime Synchronization Rule

Cursor and all developers must never mark backend or frontend work as complete while stale services are still running. A passing test suite or successful build alone does not prove the running application serves the latest code.

### Backend Changes

Whenever backend code, API routes, schemas, migrations, environment variables, or permissions change:

1. Apply all pending Alembic migrations.
2. Restart the backend server.
3. Confirm the backend runs with the correct environment.
4. Verify Swagger/OpenAPI includes the new or changed endpoints.
5. Verify at least one live API request returns the expected response.
6. Never assume an already-running backend is serving the latest code.

### Frontend Changes

Whenever frontend routes, API clients, configuration, environment variables, or Vite settings change:

1. Restart the frontend dev server.
2. Confirm the frontend is running on the actual active port.
3. Verify the affected page loads.
4. Verify browser Network requests call the expected API endpoint.
5. Never assume an already-running frontend is serving the latest code.

---

## Definition of Done

A sprint or task is **NOT complete** until all required items below are confirmed. Skip items that do not apply to the change; never skip runtime verification when backend or frontend code changed.

- [ ] Migrations applied, if required
- [ ] Backend restarted, if backend changed
- [ ] Frontend restarted, if frontend changed
- [ ] Swagger verified, if API changed
- [ ] Live API verification completed
- [ ] Affected frontend page verified
- [ ] Backend tests passed
- [ ] Frontend build passed
- [ ] Frontend tests passed, if configured
- [ ] [PROJECT_STATUS.md](PROJECT_STATUS.md) updated, if sprint completed
- [ ] [CHANGELOG.md](CHANGELOG.md) updated, if sprint completed
- [ ] Completion report provided

Sprint-specific deliverables (CRUD, pagination, archive/restore, Turkish UI, etc.) are defined in [Module Standard](#module-standard) and [Sprint Workflow](#sprint-workflow). Runtime synchronization items above are mandatory in addition to those deliverables.

### Data Integration & Universal Import Standard (ADR-016)

All import, export, and sync features must comply with these principles:

- **Import is not direct insert.** External data never bypasses preview, matching, and user decision stages.
- **Preview-first.** Upload, file analysis, mapping, and matching do not write CRM domain data.
- **No persistent writes without user decision.** Apply runs only after explicit row or bulk decisions are confirmed.
- **Fair context required.** Every import batch must have `fair_id`; `fair_name` from source data is not used (ADR-012).
- **Conservative merge.** Import does not overwrite populated CRM fields with empty or conflicting values without user approval ([docs/import/MERGE_RULES.md](docs/import/MERGE_RULES.md)).
- **Background jobs.** Import apply, export, and sync operations use the shared background job standard (queued → running → completed/failed, progress, final report).
- **Naming convention.** Backend module, API routes, database tables, and enums in **English**; frontend labels and user messages in **Turkish** (ADR-006).
- **Module identity.** Backend: `data_integration`; frontend menu: **Veri Entegrasyonu**; route: `/data-integration`.

Excel batches must declare **header mode** at setup: first row header, no header (columns A/B/C/D with sample values), or manual header row selection.

Canonical architecture: [docs/import/IMPORT_ARCHITECTURE.md](docs/import/IMPORT_ARCHITECTURE.md).

### List Screen Definition of Done (ADR-015)

A new or changed **list screen** is not complete until all of the following are verified:

- [ ] Server-side pagination
- [ ] Server-side search
- [ ] Server-side sorting
- [ ] Server-side filtering, or a documented exception in the completion report
- [ ] URL state synchronization (refresh, back, forward, shareable links)
- [ ] Loading state (initial + page change)
- [ ] Empty state (including filtered-empty variant where applicable)
- [ ] Error state with retry/refresh
- [ ] `DataTable` / `useServerDataTable` standard compliance
- [ ] No client-side `sort()` / `filter()` / `slice()` on large datasets fetched from the API

### Universal Server-Side DataTable Standard — Sorting Rule

Every list built on `UniversalDataTable` / `useServerDataTable` must follow this rule (all current and future list screens):

- **Actions / İşlemler column is never sortable** — set `sortable: false` in column definition.
- **All other displayed data columns are sortable by default** — column config `{ key, title, sortable: true }` is sufficient; `UniversalDataTable` renders sort headers automatically.
- **Sort cycle** — header click: `asc` → `desc` → clear/default.
- **Sort indicators** — inactive `↕`, active `↑` / `↓`.
- **Server-side only** — API query params `sort_by` + `sort_order`; no client-side reordering of API rows.
- **URL state** — sort persisted in query string (`sort_by`, `sort_order`); survives refresh and shareable links.
- **Backend whitelist** — each list use case defines `ALLOWED_SORT_FIELDS`; unknown fields fall back to entity default via `resolve_sort_field` / `parse_list_query` (never HTTP 400).
- **SQL safety** — sort fields mapped to fixed column references in repository; never interpolated from user input.
- **Computed columns** — sort by underlying DB field when possible (e.g. `full_name` → `last_name`).

**Architectural rule:** No list screen may decide column-by-column whether data columns are sortable. Actions excluded; everything else sortable unless an ADR documents a technical exception.

Applies to: Customers, Fairs, Participations, Contacts, Activities, Import batches, Admin backups, and all future Universal DataTable screens.

**Developer pattern:**

```typescript
const columns: UniversalDataTableColumn<Fair>[] = [
  { key: "name", title: "Fuar Adı", sortable: true, render: (row) => row.name },
  { key: "actions", title: "İşlemler", sortable: false, render: (row) => <Actions row={row} /> },
];
<UniversalDataTable table={table} columns={columns} rowKey={(r) => r.id} />
```

---

## Development Workflow

Every feature or sprint follows this workflow:

```text
Before start
  → Read PROJECT_CONSTITUTION.md, PROJECT_STATUS.md, CHANGELOG.md, docs/PRODUCT_VISION.md, docs/DECISIONS.md

Phase 1 — Design
  → ADR-009 platform reusability check
  → Design doc (domain model, API, permissions, Core integration)
  → CTO / lead review

Phase 2 — Implementation
  → Backend: domain → application → infrastructure → api → migration
  → Tests at each layer
  → Frontend: types → api → labels → components → page
  → Runtime Synchronization Rule (restart + live verification)

Phase 3 — Completion
  → Definition of Done checklist
  → Quality check (backend)
  → Frontend build
  → Completion report
  → Update PROJECT_STATUS.md
  → Update CHANGELOG.md
```

Also read `README.md`, `ROADMAP.md`, and relevant docs under `docs/` as needed for the sprint.

---

## Development Utilities / Database Safety

Fair CRM dev databases may contain real migrated data (customers, participations, import batches). **Before any destructive import test or bulk data experiment**, create a verified backup.

These utilities are **developer-only CLI helpers** — they delegate to the same shared Python backup engine as the Admin workspace. Product backup/restore is managed via **Admin → System → Database Backups** (`/admin/system/backups`).

### Shared backup engine

| Location | Role |
|----------|------|
| `backend/app/shared/database_backup/` | Single implementation for `pg_dump`, verify, checksum, path safety |
| `python -m app.shared.database_backup` | CLI used by PowerShell scripts |
| `backend/app/modules/system_admin/` | Admin API, background jobs, metadata (`system_backups`) |

### Backup / restore scripts

Run from the **repository root** (`fair-crm/`):

| Script | Purpose |
|--------|---------|
| `.\scripts\dev\backup-db.ps1` | Create a timestamped PostgreSQL custom-format backup (`.dump`) under `backups/` |
| `.\scripts\dev\list-backups.ps1` | List available backups with date/time and size |
| `.\scripts\dev\restore-db.ps1 .\backups\<file>.dump` | Restore a backup (requires explicit confirmation) |

**Configuration:** Scripts read `DATABASE_URL` from `backend/.env` (fallback: repo-root `.env`).

**Backup format:** PostgreSQL custom format via `pg_dump -Fc`. Each successful backup is verified with `pg_restore -l`.

**Restore safety:**

- `-WhatIf` / `-DryRun` validates the dump without modifying the database
- Live restore requires typing the **target database name** to confirm overwrite
- Uses `pg_restore --clean --if-exists` against the configured dev database only

**Prerequisites:** PostgreSQL client tools (`pg_dump`, `pg_restore`) on PATH, **or** the local Docker Postgres container (`kyrox-postgres-dev` from `docker compose up -d postgres`) when client tools are not installed.

**Policy:** Do not start real-data import tests until a fresh backup exists and `list-backups.ps1` shows it. The `backups/` directory is gitignored — store dumps locally only.

See also: [docs/DEV_RUNTIME.md](docs/DEV_RUNTIME.md) for dev server reset.

---

## Sprint Workflow

Sprints are numbered sequentially (Sprint 01, Sprint 02, …). Each sprint delivers one cohesive product module or capability.

### Sprint Phases

| Phase | Deliverables |
|-------|--------------|
| **Phase 1 — Design** | ADR-009 check, design doc, permission list, API sketch, CTO approval |
| **Phase 2 — Implementation** | Backend module, migration, tests, Swagger, frontend page(s) |
| **Phase 3 — Completion** | Quality gate, completion report, PROJECT_STATUS.md and CHANGELOG.md updates |

### Sprint Definition of Done

A sprint is **complete** only when [Definition of Done](#definition-of-done) is fully satisfied **and** all sprint deliverables below are implemented:

- [ ] CRUD (or sprint-specific operations) implemented
- [ ] Search, pagination, sorting (where applicable)
- [ ] Archive and restore (where entity is archivable)
- [ ] Swagger documented and verified against running backend
- [ ] Frontend UI in Turkish, verified against running dev server

### Sprint Plan

| Sprint | Module |
|--------|--------|
| 01 | Customer Management |
| 02 | Fair Management |
| 03 | Customer Contacts |
| 04 | Customer Activities |
| 05 | Customer Phones |
| 06 | Customer Emails |
| 07 | Fair Participations |
| 08 | Import Engine |
| 09 | Duplicate Detection |
| 10 | Merge Decision |
| 11 | Dashboard |
| 12 | Reporting |

---

## Completion Report Standard

At the end of every sprint (Phase 3), deliver a **Completion Report** in the sprint PR, chat, or linked document.

### Required Sections

Every completion report **must** explicitly state runtime verification status. Use `N/A` only when the category did not change.

```markdown
## Completion Report — <Sprint Name>

### Summary
One paragraph: what was delivered and sprint outcome.

### Backend
- Database table(s) and migration file(s)
- API endpoints added/changed
- Permissions used
- Notable domain rules

### Frontend
- Page(s) and components added
- Turkish labels coverage
- User flows verified

### Runtime Verification
- Migration status (applied / not required / pending)
- Backend restart status (restarted / not required)
- Frontend restart status (restarted / not required)
- Swagger verification (endpoints confirmed / N/A)
- Live API verification (request + expected response / N/A)

### Tests
- Tests executed (backend pytest, frontend build, frontend tests if configured)
- Test results (pass/fail counts, quality check outcome)

### Documentation
- PROJECT_STATUS.md updated
- CHANGELOG.md updated with version and features

### Known gaps / follow-ups
- Items deferred to future sprints (if any)
```

Keep reports factual and concise. Reference file paths for migrations, routes, and pages. Do not mark work complete in the report unless runtime verification items are confirmed or marked N/A with justification.

---

## Golden Rule

**If it belongs on the platform, it belongs in Core. If it belongs to the CRM domain, it belongs in Fair CRM. Never blur the boundary.**

Before writing code, ask:

1. Is this CRM-specific? → Build in `fair-crm`.
2. Could every KYROX product need it? → Propose for `kyrox-core` (ADR-009).
3. Does Core already provide it? → Integrate via public API — do not duplicate.
4. Does the change follow the patterns in this constitution? → Match module, pagination, archive/restore, layering, and testing standards from completed sprints.

When in conflict between speed and architecture, **architecture wins** — the cost of fixing boundary violations later exceeds the cost of doing it right once.

---

## Activity Timeline Principle

The Activity Timeline is the canonical history of all Customer and Contact interactions.

Activities may be created in two ways:

- Manually by users
- Automatically by the system

Automatic activity sources include, but are not limited to:

- Sent emails
- Email campaigns
- WhatsApp messages
- Meetings
- Calls
- Tasks
- Future communication integrations

Every automated communication with a Customer or Contact must create an Activity record.

This principle ensures that Customer history remains centralized, searchable, and auditable.

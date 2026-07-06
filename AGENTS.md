# AGENTS.md

Guidance for AI agents and automation working in the `fair-crm` repository.

This file is a short operating guide. It does not replace the project canon. When there is any conflict, follow `PROJECT_CONSTITUTION.md`, then `docs/DECISIONS.md`, then the task-specific documentation under `docs/`.

## Before Starting Work

Read these files before any new implementation sprint or architecture-sensitive task:

1. `PROJECT_CONSTITUTION.md`
2. `PROJECT_STATUS.md`
3. `CHANGELOG.md`
4. `docs/PRODUCT_VISION.md`
5. `docs/DECISIONS.md`

For local runtime or verification tasks, also read `docs/DEV_RUNTIME.md`. For import, merge, scraper, or data integration tasks, read the relevant files under `docs/import/` and `docs/architecture/`.

## Current Product State

FAIR CRM is active in development. It is not in the original Sprint 1.0 Customer-only phase.

Current delivery snapshot:

- Customer/Fair/Participation foundation modules exist.
- Adapter Management is completed.
- Linked Fairs are completed.
- Fair -> Adapter relationship is completed.
- Adapter CRUD is completed.
- Run v2 + JSON Handoff is completed.
- Current technical target: Canonical Import Schema.
- Next target: Import Batch / Preview / Duplicate / Merge pipeline.

## Repository Boundary

- Work only inside this `fair-crm` repository unless the user explicitly asks otherwise.
- Do not modify `kyrox-core` or `kyrox-platform` from this repository.
- FAIR CRM is an independent FastAPI product service with its own database.
- KYROX Core is an independent platform service. Integrate with it only through public HTTP APIs.
- Never import Core Python modules, mount Core routers, share Core database sessions, or create cross-repository foreign keys.

## Architecture Rules

- Backend modules follow `domain -> application -> infrastructure -> api`.
- Product code lives under `backend/app/modules/`.
- Shared product primitives may live under `backend/app/shared/`.
- Product database tables use the `crm_` prefix.
- `organization_id` is mandatory for org-scoped data and is a logical tenant key from Core, not a database foreign key.
- API, backend code, database names, permissions, and route names are English.
- Frontend visible labels, messages, empty states, and confirmations are Turkish.
- Platform-generic capabilities must be evaluated under ADR-009 before implementation. If the capability belongs in Core, stop and document the need instead of building it in Fair CRM.

## Data Integration, Import, and Scraper Rules

- External data must be preview-first. Do not write imported or scraped data directly to CRM records.
- Human approval is required before CRM writes.
- Import and scraper outputs must flow through the canonical import/data integration contracts where applicable.
- Fair context is required for import batches; do not infer `fair_name` from source data.
- Hall and stand data belong to fair participation records, not Customer or Fair aggregates.
- Scraper/site-specific logic belongs in scraper adapters and parsers, not in the import engine.
- Scraper adapter output field / `requested_fields` contract için `docs/import/SOURCE_ADAPTER_FRAMEWORK.md` içindeki “Scraper requested output fields contract” bölümünü oku.
- Do not change Import Preview, Merge Engine, or Adapter Builder behavior unless the user explicitly scopes that work.

## Frontend Rules

- Use React + TypeScript + Vite patterns already present in `frontend/src/`.
- Keep labels in `frontend/src/labels/`.
- Keep API calls in resource-specific files under `frontend/src/api/`.
- Use existing shared table, pagination, modal, and form patterns when modifying UI.
- List screens must use server-side pagination, search, sorting, filtering, URL state, and loading/empty/error states unless an ADR documents an exception.
- The Actions column is never sortable; other displayed data columns are sortable by default.

## Backend Rules

- Keep domain code free of FastAPI, SQLAlchemy, and HTTP client imports.
- Keep API routes thin; delegate business behavior to application use cases.
- Repositories must enforce organization scoping.
- Audit writes to Core are best-effort and must not break successful CRM mutations if Core audit is unavailable.
- Migrations live in `backend/alembic/versions/` and must affect Fair CRM product schema only.

## Verification

Choose verification proportional to the change. For backend/API changes, run the relevant pytest suite from `backend/`. For frontend changes, run `npm run build` from `frontend/`. For runtime-affecting changes, restart the affected service and verify the running app, Swagger/API, or page as required by `PROJECT_CONSTITUTION.md`.

Common checks:

```powershell
cd backend
python -m pytest

cd ..\frontend
npm run build
```

For the focused scraper/fairs workflow:

```powershell
cd backend
python -m pytest tests/modules/fairs tests/modules/scraper tests/shared
```

## Git and Change Safety

- Do not create duplicate architecture or agent-rule documents.
- Prefer updating the existing canonical document when a rule changes.
- Do not refactor, add features, or touch unrelated code while doing documentation, commit, or verification tasks.
- Never revert user changes unless explicitly requested.
- Before destructive database/import experiments, create a verified backup using the documented dev scripts.
- Keep generated build artifacts and local data out of commits unless they are intentionally part of the current task.

## Local Runtime

Use the documented dev scripts from the repository root:

```powershell
.\scripts\dev\dev-start.ps1
.\scripts\dev\dev-stop.ps1
.\scripts\dev\reset-dev.ps1
```

After restoring a database dump, always run Alembic migrations to head and restart the runtime before testing.

## Golden Rule

If it belongs to the KYROX platform, it belongs in Core. If it belongs to the CRM domain, it belongs in Fair CRM. Keep the boundary clear.

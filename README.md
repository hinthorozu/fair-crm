# FAIR CRM

FAIR CRM is the first product on the KYROX platform. It manages fair exhibitors, customers, contacts, participations, and future import/scraper workflows.

## Repository role

| Repository | Purpose |
|------------|---------|
| `kyrox-platform` | Roadmap, milestones, project management |
| `kyrox-core` | Platform service — auth, orgs, RBAC, audit, settings, jobs, notifications |
| `fair-crm` | Product service — CRM domain only |

## Current status

- **Version:** Sprint 1.0.0 Phase 2 — Customer module implemented
- **Platform dependency:** `kyrox-core v0.4.0+` (independent platform service)
- **Stack:** FastAPI + PostgreSQL (product database)

## Architecture

FAIR CRM is an **independent FastAPI service** with its own PostgreSQL database. It integrates with KYROX Core **only through public HTTP APIs** — no Python imports from kyrox-core, no shared database.

```text
Client → KYROX Core (login, orgs, RBAC)
Client → FAIR CRM (customers, …) with JWT + X-Organization-Id
FAIR CRM → KYROX Core (permission check, audit write, settings)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/INTEGRATION_WITH_CORE.md](docs/INTEGRATION_WITH_CORE.md).

## Language rules

- Backend code, database, and API: **English**
- Frontend labels and user messages: **Turkish**

## Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Running **KYROX Core** instance (default `http://localhost:8000`)

## Quick start

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Edit `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/fair_crm
JWT_SECRET_KEY=<same secret as kyrox-core>
JWT_ALGORITHM=HS256
KYROX_CORE_BASE_URL=http://localhost:8000
```

`JWT_SECRET_KEY` must match KYROX Core so Fair CRM can validate access tokens locally.

### 3. Create database

```sql
CREATE DATABASE fair_crm;
```

### 4. Run migrations

From the repository root:

```bash
alembic upgrade head
```

Product migrations live in `backend/alembic/`. They create `crm_*` tables only — never Core platform tables.

### 5. Start KYROX Core (separate terminal)

Follow [kyrox-core README](../kyrox-core/README.md). Ensure Core migrations are applied through `20260701_0025` (includes `fair_crm.customers.*` permissions).

Assign `fair_crm.customers.*` permissions to the roles your test users use.

### 6. Start Fair CRM API

```bash
cd backend
uvicorn app.main:app --reload --port 8001
```

Swagger: `http://127.0.0.1:8001/docs`

Health: `http://127.0.0.1:8001/health`

### 7. Frontend (Customer UI)

Requires **Node.js 16+** (18+ recommended).

```bash
cd frontend
cp .env.example .env   # macOS/Linux
# Windows: Copy-Item .env.example .env
npm install
npm run dev
```

Open http://127.0.0.1:5173 — Turkish UI for customer list, create, edit, search, filters, and archive.

#### Automatic dev bypass (local only)

The frontend API client (`frontend/src/config.ts` → `buildApiHeaders()`) **automatically** attaches dev-bypass headers on every request when local development rules match. No manual header wiring is needed in page or component code.

Copy `frontend/.env.example` to `frontend/.env` (optional — sensible defaults apply during `npm run dev`):

```env
VITE_API_BASE_URL=http://127.0.0.1:8001
VITE_APP_ENV=development
VITE_DEV_BYPASS_ENABLED=true
VITE_DEV_BYPASS_TOKEN=dev-bypass
VITE_ORGANIZATION_ID=00000000-0000-4000-8000-000000000010
```

**When bypass headers are sent** (non-production build only):

| Condition | Bypass active |
|-----------|---------------|
| `npm run dev` (Vite `MODE=development`) | Yes — automatic |
| `VITE_APP_ENV=development` (or `local` / `test`) | Yes |
| `VITE_DEV_BYPASS_ENABLED=true` | Yes |
| `npm run build` / production deploy | **Never** — hard-disabled via `import.meta.env.PROD` |

Headers attached in development:

```http
Authorization: Bearer dev-bypass
X-Organization-Id: 00000000-0000-4000-8000-000000000010
```

**Production behavior:** production builds never send dev-bypass headers, regardless of env vars. Integrate with the normal KYROX Core authentication flow (Bearer JWT + organization header from login).

The backend must also have dev bypass enabled for local API work — see [Dev bypass mode](#dev-bypass-mode-fair-crm-without-core) below. Restart the backend after changing `backend/.env` so `FAIR_CRM_DEV_BYPASS_CORE=true` is loaded (shell env `FAIR_CRM_DEV_BYPASS_CORE=false` overrides the file).

The backend enables CORS for local frontend origins in development mode.

## Local development environment

### PostgreSQL (Docker)

From the repository root:

```powershell
.\scripts\dev\dev-start.ps1
```

Or manually:

```bash
docker compose up -d
```

`docker compose` starts PostgreSQL on `localhost:5432` with user/password `postgres`/`postgres` (SCRAM-SHA-256, PostgreSQL 16 default). The container uses `restart: unless-stopped` so it survives Docker Desktop restarts. Use **Navicat 16+** or modern pgAdmin.

If an older client fails with `authentication method 10 not supported`, run `scripts/dev/configure-postgres-md5-auth.ps1` once (dev only). To revert after upgrading the client: `scripts/dev/configure-postgres-scram-auth.ps1`.

### Seed demo customers (dev bypass UI)

With PostgreSQL running and migrations applied, seed Turkish demo customers for the dev-bypass organization:

```bash
python scripts/seed_dev_customers.py
```

Requires `APP_ENV=development` (or `local` / `test`) in `backend/.env`. The script is **idempotent** — re-running skips customers already present (matched by `normalized_name` + organization). Seeds 14 mixed-status records (lead, active, inactive, archived) for organization `00000000-0000-4000-8000-000000000010`.

Then open the frontend at http://127.0.0.1:5173 (dev bypass headers in `frontend/.env`).

### End-to-end validation (Core + Fair CRM)

With PostgreSQL running, start both services in separate terminals:

```powershell
# Terminal 1 — KYROX Core (ensure DATABASE_URL points at kyrox_core)
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/kyrox_core"
cd ..\kyrox-core\backend
uvicorn app.main:app --port 8000

# Terminal 2 — Fair CRM
cd backend
uvicorn app.main:app --port 8001
```

Then from the fair-crm root:

```bash
python scripts/e2e_validation.py
```

The script applies migrations, seeds a dev user (`dev@example.com` / `DevPassword123!`), runs login → customer CRUD → audit verification, and writes `scripts/e2e_validation_report.json`.

> **Note:** If `DATABASE_URL` in your shell points at `fair_crm`, Core login will fail. Always set Core's database explicitly when starting kyrox-core.

### Dev bypass mode (Fair CRM without Core)

For local UI/API work without a running KYROX Core instance, enable bypass in `backend/.env`:

```env
APP_ENV=development
FAIR_CRM_DEV_BYPASS_CORE=true
FAIR_CRM_DEV_BYPASS_TOKEN=dev-bypass
```

When enabled, Fair CRM skips Core permission checks and audit writes. Authenticate with:

```http
Authorization: Bearer dev-bypass
X-Organization-Id: <any-uuid>
```

Optional: `X-Dev-User-Id` to set the synthetic user id.

Bypass is **only** allowed when `APP_ENV` is `development`, `local`, or `test`. Never enable in production.

## KYROX Core integration

| Concern | Owner | Fair CRM approach |
|---------|-------|-------------------|
| Login / refresh / logout | Core | Client calls Core directly |
| JWT validation | Fair CRM | Local decode using shared `JWT_SECRET_KEY` |
| Organization context | Header | `X-Organization-Id` on every org-scoped request |
| Permission check | Core API | `POST /organizations/{id}/authorization/check` |
| Audit write | Core API | Best-effort on customer mutations (Sprint 1) |
| Settings / jobs / notifications | Core API | Available; not used in Sprint 1 Customer module |

### Customer permissions (registered in Core)

| Permission | Use |
|------------|-----|
| `fair_crm.customers.create` | Create customer |
| `fair_crm.customers.read` | List / get customer |
| `fair_crm.customers.update` | Update customer |
| `fair_crm.customers.archive` | Archive (soft delete) customer |

### Audit behavior (Sprint 1)

Audit writes are **best-effort**. Customer create/update/archive succeeds even if the Core audit API is unavailable. Failures are logged as warnings and are not returned to API clients.

## API endpoints (Sprint 1)

Base URL: `http://localhost:8001/api/v1`

All customer routes require:

```http
Authorization: Bearer <access_token>
X-Organization-Id: <organization_uuid>
```

| Method | Path | Permission |
|--------|------|------------|
| `GET` | `/health` | — |
| `POST` | `/customers` | `fair_crm.customers.create` |
| `GET` | `/customers` | `fair_crm.customers.read` |
| `GET` | `/customers/{id}` | `fair_crm.customers.read` |
| `PATCH` | `/customers/{id}` | `fair_crm.customers.update` |
| `DELETE` | `/customers/{id}` | `fair_crm.customers.archive` |
| `POST` | `/customers/{id}/restore` | `fair_crm.customers.archive` |

List supports query params: `status`, `customer_type`, `search`, `page`, `page_size`, `sort_by`, `sort_dir`.

## Tests and quality check

From repository root:

```bash
python scripts/quality_check.py
```

Or from `backend/`:

```bash
python -m pytest -q
```

Quality check runs: Python compile, FastAPI import, and full pytest suite.

## Documentation

| Document | Content |
|----------|---------|
| [ROADMAP.md](ROADMAP.md) | Milestones and sprint status |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Service layout and module boundaries |
| [docs/INTEGRATION_WITH_CORE.md](docs/INTEGRATION_WITH_CORE.md) | Core API integration details |
| [docs/CUSTOMER_DESIGN.md](docs/CUSTOMER_DESIGN.md) | Customer aggregate design |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Product ADRs |

## Development workflow

1. Phase 1 — Design (includes platform reusability check per ADR-009)
2. CTO review
3. Phase 2 — Implementation
4. Quality check + review

Before implementation, read `README.md`, `ROADMAP.md`, and relevant docs under `docs/`.

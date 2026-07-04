# FAIR CRM

FAIR CRM is the first product on the KYROX platform. It manages fair exhibitors, customers, contacts, participations, adapter-driven data acquisition, and preview-first import workflows.

## Repository Role

| Repository | Purpose |
|------------|---------|
| `kyrox-platform` | Ecosystem roadmap, milestones, ADRs, project management |
| `kyrox-core` | Reusable SaaS platform service - auth, orgs, RBAC, audit, settings, jobs, notifications |
| `fair-crm` | Product service - CRM domain, product UI, product database, data integration workflows |

## Current Status

For detailed sprint history and quality gates, read [PROJECT_STATUS.md](PROJECT_STATUS.md). That file is the canonical project-status document.

Current product state:

- FAIR CRM is active in development.
- Customer/Fair/Participation foundations exist.
- Adapter Management is completed.
- Linked Fairs are completed.
- Fair -> Adapter relationship is completed.
- Adapter CRUD is completed.
- Run v2 + JSON Handoff is completed.
- Current technical target: Canonical Import Schema.
- Next target: Import Batch / Preview / Duplicate / Merge pipeline.

Historical note: early Sprint 1.0 documentation described the initial Customer module implementation. That milestone is no longer the live product state.

## Architecture

FAIR CRM is an **independent FastAPI product service** with its own PostgreSQL database. It integrates with KYROX Core **only through public HTTP APIs**. There are no Python imports from kyrox-core, no shared database sessions, and no cross-repository foreign keys.

```text
Client -> KYROX Core (login, orgs, RBAC)
Client -> FAIR CRM (CRM and data integration APIs) with JWT + X-Organization-Id
FAIR CRM -> KYROX Core (permission check, audit write, settings, jobs, notifications)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/INTEGRATION_WITH_CORE.md](docs/INTEGRATION_WITH_CORE.md).

## Language Rules

- Backend code, database, API paths, permissions, and route names: **English**
- Frontend labels, user messages, confirmations, and empty states: **Turkish**

## Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Node.js 18+ recommended for frontend work
- Running KYROX Core instance for full integration tests (default `http://localhost:8000`)

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Copy and edit environment settings:

```powershell
Copy-Item .env.example .env
```

Important settings:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/fair_crm
JWT_SECRET_KEY=<same secret as kyrox-core>
JWT_ALGORITHM=HS256
KYROX_CORE_BASE_URL=http://localhost:8000
```

Run product migrations from the repository root:

```bash
alembic upgrade head
```

Start the API:

```bash
cd backend
uvicorn app.main:app --reload --port 8001
```

Swagger: `http://127.0.0.1:8001/docs`  
Health: `http://127.0.0.1:8001/health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Local Development

From the repository root:

```powershell
.\scripts\dev\dev-start.ps1
```

Useful scripts:

| Script | Purpose |
|--------|---------|
| `.\scripts\dev\dev-start.ps1` | Start local development services |
| `.\scripts\dev\dev-stop.ps1` | Stop local development services |
| `.\scripts\dev\reset-dev.ps1` | Force restart stale local services |
| `.\scripts\dev\backup-db.ps1` | Create a local PostgreSQL backup |
| `.\scripts\dev\restore-db.ps1` | Restore a local PostgreSQL backup |

See [docs/DEV_RUNTIME.md](docs/DEV_RUNTIME.md).

## KYROX Core Integration

| Concern | Owner | Fair CRM approach |
|---------|-------|-------------------|
| Login / refresh / logout | Core | Client calls Core directly |
| JWT validation | Fair CRM | Local decode using shared `JWT_SECRET_KEY` |
| Organization context | Header | `X-Organization-Id` on every org-scoped request |
| Permission check | Core API | `POST /organizations/{id}/authorization/check` |
| Audit write | Core API | `POST /organizations/{id}/audit-events`, best-effort on product mutations |
| Settings / jobs / notifications | Core API | Use public Core APIs when needed |

## Development Workflow

Before implementation or architecture-sensitive work, read:

1. [PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md)
2. [PROJECT_STATUS.md](PROJECT_STATUS.md)
3. [CHANGELOG.md](CHANGELOG.md)
4. [docs/PRODUCT_VISION.md](docs/PRODUCT_VISION.md)
5. [docs/DECISIONS.md](docs/DECISIONS.md)
6. [AGENTS.md](AGENTS.md)

## Tests And Quality Check

From repository root:

```bash
python scripts/quality_check.py
```

Or from `backend/`:

```bash
python -m pytest -q
```

For frontend verification:

```bash
cd frontend
npm run build
```

## Documentation

| Document | Content |
|----------|---------|
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | Canonical sprint and quality status |
| [PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md) | Development standards and workflow |
| [ROADMAP.md](ROADMAP.md) | Current and historical roadmap |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Service layout and module boundaries |
| [docs/INTEGRATION_WITH_CORE.md](docs/INTEGRATION_WITH_CORE.md) | Core API integration details |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Product ADRs |

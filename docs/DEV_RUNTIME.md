# Fair CRM — Local Dev Runtime

This document describes how to reset the local development servers when ports are stuck or multiple stale Vite/uvicorn processes are running.

## Quick reset

From the **repository root** (`fair-crm/`):

```powershell
.\scripts\dev\reset-dev.ps1
```

The script is idempotent — safe to run multiple times.

## What it does

1. Finds processes **listening** on these ports and stops them:
   - Backend: `8001`
   - Frontend: `5173`, `5174`, `5175`, `5176`, `5177`
2. Starts the backend:

   ```text
   cd backend
   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
   ```

3. Starts the frontend with strict port binding:

   ```text
   cd frontend
   npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
   ```

4. Waits for HTTP health checks and prints URLs.

## URLs

| Service  | URL |
|----------|-----|
| Backend  | http://127.0.0.1:8001 |
| Swagger  | http://127.0.0.1:8001/docs |
| Frontend | http://127.0.0.1:5173 |
| Health   | http://127.0.0.1:8001/health |

## When to use

- Vite moved to `5174`–`5177` because `5173` was occupied
- Multiple orphaned `node` / `python` dev processes after closing terminals
- Swagger or frontend returns connection errors after a long session
- Before manual E2E testing of Smart Import Wizard or merge preview
- **After `restore-db.ps1`** — restart backend (or run `reset-dev.ps1`). A stale uvicorn process may listen on `8001` but stop responding; list screens then show infinite loading or empty data until the process is replaced.

## After database restore

1. Confirm migrations: `alembic upgrade head` (from repo root; `alembic.ini` lives there, not in `backend/`).
2. Confirm org scope: frontend `VITE_ORGANIZATION_ID` and backend `FAIR_CRM_DEV_ORGANIZATION_ID` must match `organization_id` on restored rows (default dev org: `00000000-0000-4000-8000-000000000010`).
3. Restart backend — do not reuse a hung process from before restore.
4. Smoke-test lists: `python scripts/verify_list_apis.py` (expects backend on `8001` with dev bypass headers).

## Stale process problem

Closing a terminal without stopping dev servers leaves listeners bound to ports. A new `npm run dev` then picks the next free port (5174, 5175, …).

`reset-dev.ps1` only terminates processes **bound to the listed ports** — it does not kill unrelated Node or Python processes.

## Logs

Process stdout/stderr are written to:

```text
scripts/dev/logs/backend-8001.log
scripts/dev/logs/frontend-5173.log
```

Check these files if startup verification fails.

## Prerequisites

- Python 3.12+ with backend dependencies installed (`pip install -r backend/requirements.txt`)
- Node.js 16+ with frontend dependencies (`npm install` in `frontend/`)
- PostgreSQL running and migrations applied (`alembic upgrade head` from repo root)
- Optional: KYROX Core for full auth; local dev bypass works with `FAIR_CRM_DEV_BYPASS_CORE`

## Manual start (without reset script)

See [README.md](../README.md) for full setup. Standard commands:

```powershell
# Backend
cd backend
python -m uvicorn app.main:app --reload --port 8001

# Frontend (separate terminal)
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

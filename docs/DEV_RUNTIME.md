# Fair CRM — Local Dev Runtime

Development auto-start standard: use **`dev-start.ps1`** after Windows or Docker Desktop restarts. Use **`reset-dev.ps1`** only when ports are stuck or processes are stale.

## Quick start (recommended)

From the **repository root** (`fair-crm/`):

```powershell
.\scripts\dev\dev-start.ps1
```

Idempotent — safe to run multiple times. Skips backend/frontend when health checks already pass.

## Stop runtime (keeps Docker Postgres running)

```powershell
.\scripts\dev\dev-stop.ps1
```

Stop Docker infrastructure as well:

```powershell
.\scripts\dev\dev-stop.ps1 -StopInfra
```

## Force reset (stale ports / hung uvicorn)

```powershell
.\scripts\dev\reset-dev.ps1
```

Kills listeners on backend `8001` and frontend `5173`–`5177`, then starts fresh processes.

## Scripts

| Script | Purpose |
|--------|---------|
| `dev-start.ps1` | Docker infra up + wait for Postgres (+ Redis if defined) + start backend/frontend if not healthy |
| `dev-stop.ps1` | Stop backend, frontend, optional worker; Docker infra optional via `-StopInfra` |
| `reset-dev.ps1` | Force kill stale listeners and restart backend + frontend |
| `dev-lib.ps1` | Shared helpers (sourced by the scripts above) |

## What `dev-start.ps1` does

1. Verifies Docker Engine is running
2. `docker compose up -d` (infra containers use `restart: unless-stopped`)
3. Waits for PostgreSQL health (`kyrox-postgres-dev`)
4. Waits for Redis if the `redis` service exists in `docker-compose.yml` (skipped today)
5. Starts backend only if `http://127.0.0.1:8001/health` is not OK
6. Starts frontend only if `http://127.0.0.1:5173` is not OK
7. Starts worker only if `scripts/dev/start-worker.ps1` exists (not configured in current sprint)
8. Prints service URLs and `docker compose ps`

## URLs

| Service  | URL |
|----------|-----|
| Backend  | http://localhost:8001 |
| Swagger  | http://localhost:8001/docs |
| Frontend | http://localhost:5173 |
| Health   | http://localhost:8001/health |

## Validation

```powershell
.\scripts\dev\verify-dev-auto-start.ps1
```

Runs health checks, 5× idempotency, port collision (healthy + unhealthy), and `docker compose restart postgres`. Windows reboot must be confirmed manually — see [DEV_AUTO_START_COMPLETION.md](DEV_AUTO_START_COMPLETION.md).

## After Windows restart

1. Start **Docker Desktop** (wait until Ready)
2. Run `.\scripts\dev\dev-start.ps1`

PostgreSQL may already be running via Docker `unless-stopped`; the script still ensures backend and frontend are up.

## After database restore

**Mandatory:** restored dumps reflect an older Alembic revision. Application code expects `alembic upgrade head`.

1. **Apply migrations** (from repo root): `python -m alembic upgrade head`
   - `restore-db.ps1` does this automatically; skip only if you restored by other means and forgot this step.
2. **Verify revision:** `python -m alembic current` → must show `(head)`
3. **Confirm org scope:** frontend `VITE_ORGANIZATION_ID` and backend `FAIR_CRM_DEV_ORGANIZATION_ID` match restored data
4. **Restart runtime:** `.\scripts\dev\reset-dev.ps1` (do not reuse a hung uvicorn from before restore)
5. **Smoke-test:** `python scripts/verify_list_apis.py`

### If Admin → Database Backups shows "Failed to fetch"

Usually schema drift after restore (e.g. missing `backup_format` on `system_backups`). Fix: step 1 + 4 above, then refresh the page.

## Logs

```text
scripts/dev/logs/backend-8001.log
scripts/dev/logs/frontend-5173.log
```

## Prerequisites

- Docker Desktop (PostgreSQL container)
- Python 3.12+ with `pip install -r backend/requirements.txt`
- Node.js 16+ with `npm install` in `frontend/`
- Migrations applied: `alembic upgrade head`
- Optional: KYROX Core for full auth; dev bypass works with `FAIR_CRM_DEV_BYPASS_CORE`

## Manual start (without scripts)

```powershell
docker compose up -d
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

See [README.md](../README.md) for full setup.

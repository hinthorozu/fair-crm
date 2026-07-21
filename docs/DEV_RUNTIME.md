# Fair CRM — Local Dev Runtime

Development auto-start standard: use **`dev-start.ps1`** after Windows or Docker Desktop restarts. Use **`reset-dev.ps1`** only when ports are stuck or processes are stale.

## Quick start (recommended)

Yeni bir makinede ilk kurulum:

```powershell
.\scripts\dev\setup-dev.ps1
```

Python/npm/Playwright eksiklerini kontrol eder; gerekiyorsa `pip install`, `npm install` ve `playwright install chromium` calistirir. Python, Node.js veya PostgreSQL otomatik kurulmaz.

Sadece rapor icin:

```powershell
.\scripts\dev\setup-dev.ps1 -CheckOnly
```

Ardindan runtime baslatma:

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

Kills listeners on Core `8000`, backend `8001`, and frontend `5173`–`5177`, then starts fresh processes (Core → Fair backend → frontend).

## Scripts

| Script | Purpose |
|--------|---------|
| `setup-dev.ps1` | New-machine bootstrap: check/install Python deps, npm deps, Playwright; verify .env and PostgreSQL |
| `dev-start.ps1` | Docker infra up + wait for Postgres (+ Redis if defined) + start Core/backend/frontend if not healthy |
| `dev-stop.ps1` | Stop Core, backend, frontend, optional worker; Docker infra optional via `-StopInfra` |
| `reset-dev.ps1` | Force kill stale listeners and restart Core + backend + frontend |
| `dev-lib.ps1` | Shared helpers (sourced by the scripts above) |

## What `dev-start.ps1` does

1. Verifies Docker Engine is running
2. `docker compose up -d` (infra containers use `restart: unless-stopped`)
3. Waits for PostgreSQL health (`kyrox-postgres-dev`)
4. Waits for Redis if the `redis` service exists in `docker-compose.yml` (skipped today)
5. Starts **KYROX Core** only if `http://127.0.0.1:8000/api/v1/health` is not OK (sibling `../kyrox-core` or `KYROX_CORE_ROOT`)
6. Starts Fair CRM backend only if `http://127.0.0.1:8001/health` is not OK
7. Starts frontend only if `http://127.0.0.1:5173` is not OK
8. Starts worker only if `scripts/dev/start-worker.ps1` exists (not configured in current sprint)
9. Prints service URLs and `docker compose ps`

## URLs (direct service access)

These are for **server-internal** use: health checks, Swagger, curl, and backend→Core HTTP. They are **not** browser/frontend API base URLs.

| Service  | URL |
|----------|-----|
| KYROX Core (process) | http://127.0.0.1:8000 |
| Core health | http://127.0.0.1:8000/api/v1/health |
| Fair CRM backend (process) | http://127.0.0.1:8001 |
| Swagger  | http://127.0.0.1:8001/docs |
| Frontend (Vite) | http://127.0.0.1:5173 |
| Health   | http://127.0.0.1:8001/health |

## Browser / frontend network (local = server)

Local Vite and production Nginx use the **same relative-path system**. The browser never talks to `127.0.0.1:8000` or `127.0.0.1:8001` directly. Those addresses appear only in Vite/Nginx (and backend) internal upstreams.

### FAIR CRM API

| Layer | Value |
|-------|--------|
| Browser / frontend endpoints | `/api/v1/...` |
| `VITE_API_BASE_URL` | empty (same-origin relative) |
| Local | Vite `/api` → `http://127.0.0.1:8001` |
| Server | Nginx `/api` → `http://127.0.0.1:8001` |

### KYROX Core

| Layer | Value |
|-------|--------|
| Browser / frontend endpoints | `/kyrox-core/api/v1/...` |
| `VITE_CORE_BASE_URL` | empty → frontend fallback `/kyrox-core` |
| Local | Vite `/kyrox-core` → `http://127.0.0.1:8000` |
| Server | Nginx `/kyrox-core` → `http://127.0.0.1:8000` |

### Critical rules

- Browser/frontend **never** uses `http://127.0.0.1:8000` or `http://127.0.0.1:8001` as an API base.
- `127.0.0.1` is only for Vite proxy, Nginx `proxy_pass`, systemd-bound APIs, and server-side health/curl.
- Changing public IP/domain on a new server does **not** require changing frontend `VITE_*` base URLs — keep both empty.

See `frontend/.env.example`, `frontend/vite.config.ts`, and `scripts/server/nginx/fair-crm.conf`.

## Validation

Dev auto-start smoke:

```powershell
.\scripts\dev\verify-dev-auto-start.ps1
```

Prod-path auth/RBAC gate (bypass kapalı, Core + Fair CRM ayakta olmalı):

```powershell
.\scripts\run-prod-path-e2e.ps1
# veya
python scripts/e2e_validation.py --prod-path
```

Detaylar: [CI_PROD_PATH_E2E.md](CI_PROD_PATH_E2E.md)

## Handover / memory docs (2026-07-05)

Uzun aradan sonra veya yeni geliştirici için:

| Doc | Purpose |
|-----|---------|
| [PROJECT_SNAPSHOT_2026-07-05.md](PROJECT_SNAPSHOT_2026-07-05.md) | O günkü durum — ilk okuma |
| [DEV_RESTART_GUIDE.md](DEV_RESTART_GUIDE.md) | Makineyi ayağa kaldır |
| [AUTH_RBAC_HANDOVER.md](AUTH_RBAC_HANDOVER.md) | Auth/RBAC hattı |
| [ARCHITECTURE_STATUS.md](ARCHITECTURE_STATUS.md) | Mimari özet |
| [KNOWN_DECISIONS.md](KNOWN_DECISIONS.md) | Kritik kararlar, dokunma listesi |

## After Windows restart

1. Start **Docker Desktop** (wait until Ready)
2. Run `.\scripts\dev\dev-start.ps1`

PostgreSQL may already be running via Docker `unless-stopped`; the script still ensures Core, backend, and frontend are up.

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
scripts/dev/logs/core-8000.log
scripts/dev/logs/backend-8001.log
scripts/dev/logs/frontend-5173.log
```

## Prerequisites

- Docker Desktop (PostgreSQL container)
- Sibling **kyrox-core** repo (`../kyrox-core`) or `KYROX_CORE_ROOT` env pointing at it
- Python 3.12+ with `pip install -r backend/requirements.txt` (Fair CRM and Core)
- Node.js 16+ with `npm install` in `frontend/`
- Migrations applied: `alembic upgrade head` (Fair CRM); Core migrations via Core repo
- Optional: `FAIR_CRM_DEV_BYPASS_CORE` for UI-only work without real Core auth

`setup-dev.ps1` bu maddelerin cogu icin kontrol ve kurulum adimlarini otomatiklestirir (Python/Node/PostgreSQL kurulumu haric).

## Manual start (without scripts)

```powershell
# Terminal 1 — KYROX Core (or rely on dev-start / reset-dev)
cd kyrox-core\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — Fair CRM backend
cd fair-crm\backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

# Terminal 3 — Frontend
cd fair-crm\frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

See [README.md](../README.md) for full setup.

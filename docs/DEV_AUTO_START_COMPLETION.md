# Development Auto Start — Completion Report

**Sprint:** Development Auto Start Standard  
**Date:** 2026-07-02  
**Scope:** Development runtime automation only (no business logic changes)

---

## Summary

Fair CRM local development can be brought up after Windows or Docker restarts with a single idempotent command:

```powershell
cd fair-crm
.\scripts\dev\dev-start.ps1
```

Automated validation: `.\scripts\dev\verify-dev-auto-start.ps1`

---

## Changed Files

| File | Change |
|------|--------|
| `docker-compose.yml` | Added `restart: unless-stopped` on `postgres` |
| `scripts/dev/dev-lib.ps1` | **New** — shared Docker/runtime helpers |
| `scripts/dev/dev-start.ps1` | **New** — idempotent auto-start |
| `scripts/dev/dev-stop.ps1` | **New** — stop runtime; optional `-StopInfra` |
| `scripts/dev/reset-dev.ps1` | Refactored to use `dev-lib.ps1` |
| `scripts/dev/verify-dev-auto-start.ps1` | **New** — automated validation suite |
| `docs/DEV_RUNTIME.md` | Auto-start workflow documented |
| `PROJECT_CONSTITUTION.md` | Dev utilities table + restart policy note |
| `PROJECT_STATUS.md` | Development Runtime section |
| `CHANGELOG.md` | Unreleased entry |
| `README.md` | Points to `dev-start.ps1` |

---

## Restart Policies Added

| Service | Policy | Notes |
|---------|--------|-------|
| `postgres` | `unless-stopped` | Only long-running infra service in compose today |

**Not in compose (skipped by scripts):** Redis, pgAdmin, MinIO, worker, scheduler — `dev-start.ps1` detects services via `docker compose config --services` and skips waits when undefined.

---

## Script Behavior

### `dev-start.ps1` (idempotent)

1. Fail fast if Docker Engine is not running
2. `docker compose up -d`
3. Wait for PostgreSQL health on `kyrox-postgres-dev`
4. Wait for Redis only if `redis` service exists
5. Start backend on `8001` only if `/health` is not OK
6. Start frontend on `5173` only if HTTP check fails
7. Start worker only if `scripts/dev/start-worker.ps1` exists
8. Print port report, `docker compose ps`, and URLs

Duplicate prevention: if port is listening but health check fails → error with hint to run `reset-dev.ps1`.

### `dev-stop.ps1`

- Stops uvicorn, vite, optional worker launcher, and port listeners on `8001` / `5173`
- Does **not** stop Docker infra by default
- `-StopInfra` runs `docker compose stop`

### `reset-dev.ps1`

- Force kill listeners on `8001`, `5173`–`5177`
- Always starts fresh backend + frontend
- OpenAPI participants-list verification retained

Hot reload preserved: backend uses `uvicorn --reload`, frontend uses Vite dev server.

---

## Validation Results (2026-07-02)

Command: `.\scripts\dev\verify-dev-auto-start.ps1`  
Automated: **PASS=6 FAIL=0 SKIP=0** (exit code 0)  
Manual Windows reboot: **PASS** (sign-off 2026-07-02)

| # | Test | Status | Detail |
|---|------|--------|--------|
| 1 | **Windows reboot** | **PASS** | Manual sign-off 2026-07-02: reboot → Docker Ready → `dev-start.ps1` only → Postgres healthy, backend :8001, frontend :5173 |
| 2 | **Docker restart** | **PASS** | `docker compose restart postgres` → healthy; `dev-start.ps1` OK; backend `/health` + frontend `index.html` OK |
| 3 | **Idempotency (5×)** | **PASS** | Backend listeners=1, Frontend listeners=1 after five consecutive `dev-start.ps1` runs |
| 4a | **Port collision — healthy** | **PASS** | Existing healthy processes on 8001/5173 reused; no duplicates |
| 4b | **Port collision — unhealthy** | **PASS** | Port 5173 blocked (TcpListener) without HTTP → `dev-start.ps1` throws: *"Port 5173 is in use but frontend is not responding..."* |
| 5a | **Health — Backend HTTP** | **PASS** | `GET /health` → `{"status":"ok","service":"fair-crm","version":"1.0.0-phase2"}` |
| 5b | **Health — Frontend HTTP** | **PASS** | `http://127.0.0.1:5173/index.html` → 200 |

### Manual tests still required

#### 2. Docker Desktop full restart (optional)

1. Quit Docker Desktop completely (not just restart container)
2. Start Docker Desktop → **Ready**
3. Confirm Postgres auto-starts (`unless-stopped`)
4. Run `.\scripts\dev\dev-start.ps1`
5. Confirm backend + frontend URLs

> **Note:** Automated test used `docker compose restart postgres` (container-level). Windows reboot manual sign-off (2026-07-02) covers the primary acceptance path.

---

## Bugfixes During Validation

| Issue | Fix |
|-------|-----|
| `docker info` stderr warnings treated as fatal under `$ErrorActionPreference Stop` | `Test-DockerEngineReady` sets `$ErrorActionPreference = Continue` during check |
| `docker compose up` stderr broke idempotency loop | `Invoke-DevDockerCompose` wrapper suppresses native stderr errors |
| `$backendStarted` unset under `Set-StrictMode` | Initialize `$backendStarted` / `$frontendStarted` before branches in `dev-start.ps1` |

---

## Service URLs

| Service | URL |
|---------|-----|
| Backend (process) | http://127.0.0.1:8001 |
| Swagger | http://127.0.0.1:8001/docs |
| Frontend UI | http://127.0.0.1:5173 |
| Health | http://127.0.0.1:8001/health |
| Browser → Fair CRM API | `/api/v1/...` (Vite proxy → 8001) |
| Browser → Core | `/kyrox-core/api/v1/...` (Vite proxy → 8000) |

Canonical network rules: [DEV_RUNTIME.md](DEV_RUNTIME.md#browser--frontend-network-local--server).

---

## Known Gaps

1. **Windows reboot** — requires one manual confirmation per machine (see procedure above).
2. **Docker Desktop full quit/reopen** — not automated; `unless-stopped` + manual check recommended once.
3. **Backend/frontend are host processes** — survive Docker restart but not Windows reboot without `dev-start.ps1`.
4. **Worker** — no `start-worker.ps1`; import apply uses in-process `BackgroundTasks`.
5. **Redis / pgAdmin / MinIO** — not in compose; add with `restart: unless-stopped` when introduced.

---

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| `docker compose ps` shows infra Up/healthy | ✅ Verified in validation run |
| `dev-start.ps1` single-command ready state | ✅ PASS |
| `dev-stop.ps1` cleans runtime processes | ✅ Implemented (not in automated suite) |
| No duplicate backend/frontend on re-run | ✅ PASS (5× idempotency) |
| Hot reload preserved | ✅ `--reload` / Vite dev unchanged |
| Business logic unchanged | ✅ Scripts/docs/compose only |
| Port collision handling | ✅ PASS (healthy reuse + unhealthy error) |
| HTTP health checks | ✅ PASS |

**Sprint status:** **COMPLETE** — approved for merge (2026-07-02).

**Manual sign-off:** Windows reboot → `dev-start.ps1` only → PostgreSQL healthy, backend :8001, frontend :5173. **PASS**

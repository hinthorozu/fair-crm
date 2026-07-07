# Server deploy — KYROX Core + Fair CRM

Three-script workflow for repeatable Ubuntu server setup and diagnosis.

```bash
sudo bash scripts/server/bootstrap-server.sh
sudo bash scripts/server/deploy-all.sh
sudo bash scripts/server/check-server.sh
```

## check-server.sh output format

```text
FAIR CRM Server Check

[OK] Docker installed
[OK] Core health 200
[OK] Login smoke test passed
[WARN] 443 not configured
[FAIL] ...

Final: HEALTHY | DEGRADED | BROKEN
```

- **HEALTHY** — no failures, no warnings
- **DEGRADED** — warnings only (e.g. 443 not configured, Postgres bound to 0.0.0.0 via Docker)
- **BROKEN** — one or more `[FAIL]` checks

Set `CHECK_STRICT=1` to treat warnings as failure (exit 1).

## Login smoke test

Both `deploy-all.sh` and `check-server.sh` POST to:

`http://127.0.0.1:8000/api/v1/auth/login`

with `dev@example.com` / `DevPassword123!` and require HTTP 200 + `access_token`.

## Port binding expectations

| Service    | Expected bind        |
|-----------|----------------------|
| PostgreSQL | 127.0.0.1:5432 — repo default and bootstrap patch `"5432:5432"` → `"127.0.0.1:5432:5432"` |
| KYROX Core | 127.0.0.1:8000 (FAIL if 0.0.0.0) |
| Fair CRM   | 127.0.0.1:8001 (FAIL if 0.0.0.0) |
| Nginx      | public :80 (and :443 optional) |

## UFW checks

- `[OK] 22 allowed`, `[OK] 80 allowed`
- `[WARN] 443 not configured` if no HTTPS rule
- `[OK] 5432/8000/8001 not publicly exposed`

## systemd templates

- `Restart=always`, `RestartSec=5`
- Bind `127.0.0.1` only for API services
- Templates: `scripts/server/systemd/kyrox-core.service`, `fair-crm-backend.service`

## Protected files (never overwritten)

- `docker-compose.yml`, all `.env` files, custom nginx site config
- `backups/`, `data/restore_uploads/`, `data/restore_logs/` (git pull tolerates local changes; deploy never deletes contents)

See script headers for `SKIP_*` and path override variables.

## Backup / restore coexistence

Restore development and production restore jobs do **not** conflict with the server deploy scripts:

| Script | Role |
|--------|------|
| `bootstrap-server.sh` | OS packages, Docker, nginx, Postgres container, env scaffolding — **no** migrations or restore |
| `deploy-all.sh` | Code update, `alembic upgrade head`, systemd restart — **no** DB reset or restore execution |
| `scripts/dev/run-restore-job.ps1` | Destructive restore runner (dev); requires `ALLOW_RESTORE=true` and explicit `TARGET_DATABASE_URL` |
| `scripts/server/run-restore-job.sh` | Same runner on Linux server; **not** called by `deploy-all.sh` |

**After a database restore** (dev or server), always run pending migrations before relying on the API:

```bash
# deploy-all.sh does this automatically on server:
python -m alembic upgrade head   # from fair-crm repo root / backend venv
```

`deploy-all.sh` intentionally:

- Applies **Alembic upgrade head** on Core and Fair CRM (schema catch-up; preserves existing rows including `system_backup_restore_jobs`)
- Restarts `fair-crm-backend` via systemd
- **Does not** drop/truncate databases, run `pg_restore`, delete backup files, or overwrite `.env`
- **Does not** set or clear `ALLOW_RESTORE`, `TARGET_DATABASE_URL`, or other restore guard env vars

Destructive restore remains a separate, explicitly guarded operation:

```bash
# Dev (Windows)
$env:ALLOW_RESTORE = "true"
$env:TARGET_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/fair_crm"
.\scripts\dev\run-restore-job.ps1 -RestoreJobId "<job-id>"

# Server (Linux) — manual only; deploy-all.sh never runs this
export ALLOW_RESTORE=true
export TARGET_DATABASE_URL='postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/fair_crm'
sudo -E /opt/fair-crm/scripts/server/run-restore-job.sh <job-id>
# optional: RESTART_BACKEND=1 sudo -E .../run-restore-job.sh <job-id>
```

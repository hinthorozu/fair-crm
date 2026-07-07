# Server deploy — KYROX Core + Fair CRM

Single-command bootstrap/update for a Linux server with both platform services.

## Command

```bash
sudo /opt/fair-crm/scripts/server/deploy-all.sh
```

Run from the Fair CRM checkout on the server. The script is idempotent and safe to re-run.

## What it does

1. Ensures `/opt/kyrox-core` and `/opt/fair-crm` exist (clone or `git pull --ff-only`)
2. Installs Python deps into project-local virtualenvs:
   - `/opt/kyrox-core/.venv`
   - `/opt/fair-crm/backend/.venv`
3. Starts Postgres via existing `docker-compose.yml` (does **not** overwrite compose/env)
4. Verifies DB connectivity and creates `kyrox_core` / `fair_crm` databases if missing
5. Validates `.env` files (must exist; deploy never creates or overwrites them)
6. Checks `JWT_SECRET_KEY` matches between Core and Fair CRM
7. Runs Alembic `upgrade head` for both projects
8. Runs Core dev identity seed (`scripts/seed_fair_crm_dev_identity.py`)
9. Installs/updates systemd units and restarts services
10. Builds frontend (`npm install` + `npm run build` → `frontend/dist`)
11. Health checks:
    - Core: `http://127.0.0.1:8000/api/v1/health`
    - Fair CRM: `http://127.0.0.1:8001/health`

## Protected server files (never overwritten by deploy)

- `/opt/fair-crm/docker-compose.yml` (custom Postgres password/port preserved)
- `/opt/fair-crm/backend/.env`
- `/opt/fair-crm/frontend/.env` / `.env.production`
- `/opt/kyrox-core/backend/.env`

If other tracked files have local modifications, deploy aborts instead of clobbering server state.

## Environment overrides

| Variable | Default | Purpose |
|----------|---------|---------|
| `KYROX_CORE_DIR` | `/opt/kyrox-core` | Core checkout path |
| `FAIR_CRM_DIR` | repo root | Fair CRM checkout path |
| `KYROX_CORE_REPO` | `https://github.com/hinthorozu/kyrox-core.git` | Clone URL |
| `KYROX_CORE_BRANCH` | `main` | Core branch |
| `FAIR_CRM_BRANCH` | `feat/dev-auto-start-v1` | Fair CRM branch |
| `DEPLOY_SERVICE_USER` | current user | systemd `User=` |
| `SKIP_FRONTEND_BUILD` | `0` | Set `1` to skip npm build |
| `SKIP_CORE_DEV_SEED` | `0` | Set `1` to skip Core dev identity seed |
| `SKIP_SYSTEMD` | `0` | Set `1` to skip systemd install/restart |

## Prerequisites on server

- `git`, `python3`, `python3-venv`, `pip`, `psql`, `curl`, `npm`, `node`
- `docker` + `docker compose` if using bundled Postgres
- `sudo` for systemd unit install (optional with `SKIP_SYSTEMD=1`)

## Manual first-time setup (before first deploy)

```bash
# Fair CRM (once)
sudo mkdir -p /opt/fair-crm
sudo git clone https://github.com/hinthorozu/fair-crm.git /opt/fair-crm
cp /opt/fair-crm/backend/.env.example /opt/fair-crm/backend/.env
# edit backend/.env: DATABASE_URL, JWT_SECRET_KEY (match Core), KYROX_CORE_BASE_URL

# Core (deploy script can clone; or manually)
cp /opt/kyrox-core/backend/.env.example /opt/kyrox-core/backend/.env
# edit JWT_SECRET_KEY to match Fair CRM

# Optional frontend production env
cp /opt/fair-crm/frontend/.env.example /opt/fair-crm/frontend/.env.production
# set VITE_CORE_BASE_URL to public Core URL if UI is served separately
```

## systemd services

Templates live in `scripts/server/systemd/`:

- `kyrox-core.service` → port **8000**
- `fair-crm-backend.service` → port **8001**

## Post-deploy UI verification

- `/login` opens
- Login with dev credentials
- Dashboard loads real data
- Customers API returns 200
- Logout works

## Related

- Local dev: `docs/DEV_RUNTIME.md`
- Prod-path auth gate: `docs/CI_PROD_PATH_E2E.md`

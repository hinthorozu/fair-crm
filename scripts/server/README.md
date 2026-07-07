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

See script headers for `SKIP_*` and path override variables.

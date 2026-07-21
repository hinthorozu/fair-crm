# Prod-Path E2E CI Gate

Fair CRM auth/RBAC doğrulaması için prod-path kalite kapısı. Dev bypass kapalıyken gerçek JWT, Core authorization API ve role matrix live kontrollerini çalıştırır.

## Hızlı başlangıç (lokal)

```powershell
# 1. Altyapı + servisler (bypass kapalı)
$env:FAIR_CRM_DEV_BYPASS_CORE = "false"
.\scripts\dev\reset-dev.ps1

# 2. kyrox-core sibling olarak mevcut olmalı (../kyrox-core)
#    Core port 8000, Fair CRM port 8001

# 3. Prod-path gate
python scripts/e2e_validation.py --prod-path
```

PowerShell wrapper:

```powershell
.\scripts\run-prod-path-e2e.ps1
```

CI alias (aynı davranış):

```powershell
python scripts/e2e_validation.py --ci
```

## Gerekli ortam

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `FAIR_CRM_DEV_BYPASS_CORE` | `false` | **Prod-path için zorunlu false.** `true` ise gate fail eder. |
| `KYROX_CORE_BASE_URL` | `http://127.0.0.1:8000` | Core API (**E2E script / server-internal**; browser uses `/kyrox-core`) |
| `FAIR_CRM_BASE_URL` | `http://127.0.0.1:8001` | Fair CRM API (**E2E script / server-internal**; browser uses `/api/v1/...`) |
| `KYROX_CORE_DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/kyrox_core` | Core DB (seed) |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5432/fair_crm` | Fair CRM DB |
| `FAIR_CRM_DEV_ORGANIZATION_ID` | `00000000-0000-4000-8000-000000000010` | Seed org |
| `KYROX_CORE_ROOT` | *(otomatik)* | kyrox-core yolu; sibling veya repo içi `kyrox-core/` |

## Beklenen servis portları

| Servis | Port | Health |
|--------|------|--------|
| KYROX Core | 8000 | `GET /api/v1/health` |
| Fair CRM | 8001 | `GET /health` |
| PostgreSQL | 5432 | — |

## Prod-path modu (`--prod-path` / `--ci`)

Fail-fast sırası:

1. **Env guard** — `FAIR_CRM_DEV_BYPASS_CORE=false`
2. **PostgreSQL** erişilebilir
3. **Erken servis health** — Core + Fair CRM ayakta mı?
4. **Erken bypass probe** — `Bearer dev-bypass` → 401/403 (200 ise fail)
5. Core migrations + revision guard (`>= 20260701_0026`)
6. Dev identity seed + `.dev_state.json` doğrulama (`role_matrix_version`)
7. Seed idempotency (2. çalıştırma, duplicate mapping yok)
8. Pytest: `test_endpoint_permission_enforcement.py`, `test_role_matrix_authorization.py`
9. Live auth: owner/admin, viewer, sales, scraper_operator, foreign org, scope mismatch
10. Customer flow (adım 15–19) — mevcut E2E akışı korunur

## Koşulan testler

| Suite | Dosya |
|-------|-------|
| Endpoint permission enforcement | `backend/tests/modules/test_endpoint_permission_enforcement.py` |
| Role matrix authorization | `backend/tests/modules/test_role_matrix_authorization.py` |

Live kontroller (14b):

- **owner/admin** — customers + admin backups erişimi
- **viewer** — GET ok, POST 403
- **sales** — customer create ok, admin backups 403
- **scraper_operator** — scraper runs ok, customer create 403, fair run 202
- **foreign org** — Core + Fair CRM 403/400
- **dev-bypass** — her path için reddedilir

## Çıktı

- Her adım `[PASS]` / `[FAIL]`
- Fail adımlarında `hint:` / `fix:` önerisi
- Toplam süre (`Duration: …s`)
- Runtime config özeti
- JSON rapor: `scripts/e2e_validation_report.json`

## Sık hata sebepleri

| Belirti | Olası neden | Çözüm |
|---------|-------------|-------|
| `0. Prod-path env guard` fail | `FAIR_CRM_DEV_BYPASS_CORE=true` | `backend/.env` düzelt, `reset-dev.ps1` |
| `0b` / `9b` dev-bypass probe fail | Eski uvicorn veya bypass açık | Port 8001 dinleyicisini öldür, `reset-dev.ps1` |
| `4. kyrox-core running` fail | Core kapalı veya port 8000 meşgul | Core'u güncel kodla başlat |
| `3b. Core migration revision` fail | Eski Core DB / migration eksik | `cd kyrox-core && python -m alembic upgrade head` |
| `11. Verify seed state` fail | Stale `.dev_state.json` | `python scripts/seed_core_dev_identity.py` |
| `11f` role matrix SQL fail | Eksik role-permission mapping | Seed'i yeniden çalıştır |
| `11c` idempotency fail | Duplicate `identity_role_permissions` | Seed script idempotent olmalı; DB'yi kontrol et |
| `14b` live auth fail | Core authorization stale | Core restart + seed |

## CI (GitHub Actions)

Workflow: `.github/workflows/prod-path-e2e.yml`

`kyrox-core` deposu aynı workspace'e checkout edilir (`KYROX_CORE_ROOT`). Job PostgreSQL service container kullanır, Core ve Fair CRM'yi bypass kapalı başlatır, ardından:

```bash
python scripts/e2e_validation.py --ci
```

## İlgili dosyalar

- `scripts/e2e_validation.py` — ana gate
- `scripts/run-prod-path-e2e.ps1` — lokal wrapper
- `scripts/seed_core_dev_identity.py` — dev RBAC seed
- `scripts/fair_crm_role_matrix.py` — merkezi role matrix (`ROLE_MATRIX_VERSION`)
- `scripts/.dev_state.json` — seed çıktısı (gitignore)

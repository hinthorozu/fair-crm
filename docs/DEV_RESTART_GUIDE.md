# FAIR CRM — Dev Restart Guide

**Amaç:** Projeye uzun aradan sonra (veya yeni makinede) Fair CRM + Core + auth/RBAC hattını çalışır hale getirmek.  
**Son güncelleme:** 2026-07-05  
**Süre tahmini:** 15–30 dakika (ilk kurulum hariç)

---

## Ön koşullar

- Docker Desktop (PostgreSQL)
- Python 3.12+
- Node.js 16+
- **kyrox-core** repo, fair-crm ile sibling: `../kyrox-core` (veya `KYROX_CORE_ROOT` env)
- Git clone: `fair-crm` + `kyrox-core`

---

## Adım 1 — İlk kurulum (yeni makine)

```powershell
cd fair-crm
.\scripts\dev\setup-dev.ps1
```

Python/npm bağımlılıkları, Playwright, `.env` kontrolleri.

---

## Adım 2 — Altyapı

```powershell
docker compose up -d
```

PostgreSQL container'ının healthy olduğunu doğrula:

```powershell
docker compose ps
```

---

## Adım 3 — Veritabanı migration'ları

**Core (zorunlu — permission catalog burada):**

```powershell
cd ..\kyrox-core
python -m alembic upgrade head
python -m alembic current   # >= 20260701_0026 olmalı
```

**Fair CRM:**

```powershell
cd ..\fair-crm
python -m alembic upgrade head
python -m alembic current   # (head) olmalı
```

> DB restore yaptıysan: restore sonrası **mutlaka** her iki repo için `alembic upgrade head`, ardından `reset-dev.ps1`. Bkz. [DEV_RUNTIME.md](DEV_RUNTIME.md#after-database-restore).

---

## Adım 4 — Dev identity seed (Core RBAC)

```powershell
cd fair-crm
python scripts/seed_core_dev_identity.py
```

Başarılı ise `scripts/.dev_state.json` oluşur.

Doğrulama:

```powershell
Get-Content scripts\.dev_state.json | ConvertFrom-Json | Select-Object organization_id, role_matrix_version
```

Beklenen: `role_matrix_version = 1`, 6 rol under `roles`.

---

## Adım 5 — Backend `.env` (kritik)

`backend/.env` (veya ortam değişkenleri):

```env
APP_ENV=development
FAIR_CRM_DEV_BYPASS_CORE=false
JWT_SECRET_KEY=<Core ile aynı değer>
KYROX_CORE_BASE_URL=http://127.0.0.1:8000
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/fair_crm
```

**Prod-path test ve gerçek RBAC için bypass kapalı olmalı.**

Core `backend/.env` içinde de `JWT_SECRET_KEY` Fair CRM ile eşleşmeli.

---

## Adım 6 — Servisleri başlat

### Seçenek A — Script (önerilen)

```powershell
cd fair-crm
$env:FAIR_CRM_DEV_BYPASS_CORE = "false"
.\scripts\dev\reset-dev.ps1
```

`reset-dev.ps1` port 8000/8001/5173'teki eski process'leri öldürüp yeniden başlatır (önce Core, sonra Fair backend, sonra frontend).

Core sibling repo gerekir: `../kyrox-core` veya `KYROX_CORE_ROOT`.

### Seçenek B — Manuel

```powershell
# Terminal 1 — Core
cd kyrox-core\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — Fair CRM
cd fair-crm\backend
$env:FAIR_CRM_DEV_BYPASS_CORE = "false"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001

# Terminal 3 — Frontend
cd fair-crm\frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

---

## Adım 7 — Health check

```powershell
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8001/health
```

Bypass kapalı doğrulama (200 dönmemeli):

```powershell
curl -H "Authorization: Bearer dev-bypass" -H "X-Organization-Id: 00000000-0000-4000-8000-000000000010" http://127.0.0.1:8001/api/v1/customers
```

Beklenen: **401** veya **403** (200 ise bypass hâlâ açık — `reset-dev.ps1` tekrar).

---

## Adım 8 — Prod-path E2E gate

```powershell
cd fair-crm
$env:FAIR_CRM_DEV_BYPASS_CORE = "false"
python scripts/e2e_validation.py --prod-path
```

veya:

```powershell
.\scripts\run-prod-path-e2e.ps1
```

Tüm adımlar `[PASS]` ise auth/RBAC hattı sağlıklı.

Rapor: `scripts/e2e_validation_report.json`

---

## Adım 9 — Hızlı pytest (servis gerekmez)

```powershell
cd fair-crm\backend
python -m pytest tests/modules/test_endpoint_permission_enforcement.py tests/modules/test_role_matrix_authorization.py -q
```

Beklenen: 73 passed.

---

## Günlük kullanım

| Durum | Komut |
|-------|-------|
| Windows / Docker restart sonrası | `.\scripts\dev\dev-start.ps1` (Core + Fair backend + frontend) |
| Port stuck / eski uvicorn | `.\scripts\dev\reset-dev.ps1` |
| Gün sonu | `.\scripts\dev\dev-stop.ps1` |
| Auth garip davranıyor | Seed + reset-dev + prod-path e2e |

---

## Sık sorunlar

| Sorun | Çözüm |
|-------|-------|
| E2E adım **0b** fail | Fair CRM bypass açık; `.env` → `false`, `reset-dev.ps1` |
| E2E adım **4/5** fail | Core (8000) veya Fair (8001) kapalı |
| 403 her yerde | `python scripts/seed_core_dev_identity.py` |
| JWT invalid | `JWT_SECRET_KEY` Core ↔ Fair CRM eşleşmesi |
| Migration hatası | Her iki repo `alembic upgrade head` |
| Admin backups "Failed to fetch" | Fair CRM migration eksik (restore sonrası) |
| kyrox-core bulunamadı | Clone sibling veya `KYROX_CORE_ROOT=C:\path\to\kyrox-core` |

---

## Dev login bilgileri

Seed sonrası (`.dev_state.json` email/org; şifre ortam değişkeninden):

- **Owner:** `dev@example.com`
- **Password:** `$env:DEV_USER_PASSWORD` (sunucuda `/etc/fair-crm/dev-seed.env`)
- **Org ID:** 00000000-0000-4000-8000-000000000010

Seed:

```powershell
$env:DEV_USER_PASSWORD = "<dev-password>"
python scripts/seed_core_dev_identity.py
```

Core login:

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/auth/login -H "Content-Type: application/json" -d "{\"email\":\"dev@example.com\",\"password\":\"$env:DEV_USER_PASSWORD\"}"
```

---

## İlgili dokümanlar

- [AUTH_RBAC_HANDOVER.md](AUTH_RBAC_HANDOVER.md) — RBAC detayı
- [CI_PROD_PATH_E2E.md](CI_PROD_PATH_E2E.md) — E2E adımları
- [DEV_RUNTIME.md](DEV_RUNTIME.md) — script referansı
- [PROJECT_SNAPSHOT_2026-07-05.md](PROJECT_SNAPSHOT_2026-07-05.md) — son bilinen durum

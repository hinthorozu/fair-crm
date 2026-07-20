# FAIR CRM — Project Snapshot (2026-07-05)

**Tarih:** 2026-07-05  
**Amaç:** Bu tarihteki proje durumunun dondurulmuş özeti — 3 ay sonra ilk okunacak dosya.

---

## Tek cümle özet

**FAIR CRM auth/RBAC altyapısı tamamlandı.** Permission catalog, role matrix, endpoint enforcement, prod-path E2E ve CI gate hazır.

---

## Tamamlanan auth/RBAC hattı

| Parça | Durum | Not |
|-------|-------|-----|
| Core permission catalog (40 `fair_crm.*`) | ✅ | kyrox-core `20260701_0026` |
| Nested permission codes | ✅ | Core API 400 on invalid code |
| Endpoint-level permission guards | ✅ | Tüm ana modüller audit edildi |
| Central role matrix | ✅ | `scripts/fair_crm_role_matrix.py`, v1 |
| Dev seed (6 rol, 6 kullanıcı) | ✅ | Idempotent |
| `.dev_state.json` | ✅ | Seed çıktısı, E2E input |
| Pytest security suites (73 test) | ✅ | Enforcement + role matrix |
| Prod-path E2E | ✅ | `scripts/e2e_validation.py --prod-path` |
| CI workflow | ✅ | `.github/workflows/prod-path-e2e.yml` |

---

## Son bilinen durum (2026-07-05)

Prod-path E2E gate lokal ortamda **adım 0b'de fail** etti:

```text
[FAIL] 0b. Early prod-path guard (live dev-bypass probe)
       Fair CRM accepted Bearer dev-bypass (status=200)
```

**Bu beklenen ve doğru davranış.** Çalışan Fair CRM process'i `FAIR_CRM_DEV_BYPASS_CORE=true` (veya eski uvicorn) ile ayaktaydı. Gate, bypass açıkken bilerek durur — prod-path güvenlik kontrolünün çalıştığını kanıtlar.

Diğer erken adımlar geçti:

- PostgreSQL reachable
- Core health 8000 OK
- Fair CRM health 8001 OK
- Env guard: `FAIR_CRM_DEV_BYPASS_CORE=false` (E2E runner tarafında)

Pytest suite'leri (servis gerektirmeden): **73 passed**.

---

## Devam etmek için (hemen)

1. **Fair CRM'yi bypass kapalı restart et:**

   ```powershell
   # backend/.env
   FAIR_CRM_DEV_BYPASS_CORE=false

   cd fair-crm
   .\scripts\dev\reset-dev.ps1
   ```

2. **Core ayakta olduğundan emin ol** (port 8000).

3. **Prod-path gate çalıştır:**

   ```powershell
   python scripts/e2e_validation.py --prod-path
   ```

4. Tüm adımlar `[PASS]` olmalı (0b dahil).

---

## Kritik dosyalar (auth)

| Dosya | Rol |
|-------|-----|
| `scripts/fair_crm_role_matrix.py` | Role → permission tanımı |
| `scripts/seed_core_dev_identity.py` | Core DB dev seed |
| `scripts/.dev_state.json` | Seed state (gitignore) |
| `scripts/e2e_validation.py` | Prod-path E2E gate |
| `scripts/run-prod-path-e2e.ps1` | Lokal wrapper |
| `backend/app/integrations/kyrox_core/` | Core HTTP + dev bypass |
| `backend/tests/modules/test_endpoint_permission_enforcement.py` | Route guard tests |
| `backend/tests/modules/test_role_matrix_authorization.py` | Matrix tests |

---

## Dev kullanıcılar (seed)

Şifre: `DEV_USER_PASSWORD` env (sunucu: `/etc/fair-crm/dev-seed.env`) · Org: `00000000-0000-4000-8000-000000000010`

| Rol | E-posta |
|-----|---------|
| owner | dev@example.com |
| admin | dev-admin@example.com |
| manager | dev-manager@example.com |
| sales | dev-sales@example.com |
| viewer | dev-viewer@example.com |
| scraper_operator | dev-scraper@example.com |

---

## Product durumu (kısa)

Fair CRM aktif geliştirmede; Customer/Fair/Contact/Participation/Activity, Import, Scraper, SMTP, System Admin modülleri mevcut. Tam feature listesi: [PROJECT_STATUS.md](../PROJECT_STATUS.md).

Sıradaki product hedefleri (auth dışı): Import batch / preview / duplicate / merge pipeline, canonical import schema.

---

## Okuma sırası (3 ay sonra)

1. **Bu dosya** — nerede kaldık
2. [DEV_RESTART_GUIDE.md](DEV_RESTART_GUIDE.md) — makineyi ayağa kaldır
3. [AUTH_RBAC_HANDOVER.md](AUTH_RBAC_HANDOVER.md) — RBAC nasıl çalışır
4. [KNOWN_DECISIONS.md](KNOWN_DECISIONS.md) — dokunma listesi
5. [CI_PROD_PATH_E2E.md](CI_PROD_PATH_E2E.md) — gate detayı

---

## Versiyon referansları

| Bileşen | Değer |
|---------|-------|
| Role matrix version | `1` |
| Min Core migration | `20260701_0026` |
| Fair CRM permissions | 40 (`fair_crm.*`) |
| Owner permissions | 40 + `audit.logs.read` |

---

*Bu snapshot değiştirilmez; yeni durum için yeni tarihli snapshot veya PROJECT_STATUS güncellemesi kullanılır.*

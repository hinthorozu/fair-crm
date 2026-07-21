# FAIR CRM — Architecture Status

**Amaç:** Proje mimarisinin ve entegrasyon sınırlarının güncel özeti.  
**Son güncelleme:** 2026-07-05  
**Canlı durum:** [PROJECT_STATUS.md](../PROJECT_STATUS.md) · **Anlık snapshot:** [PROJECT_SNAPSHOT_2026-07-05.md](PROJECT_SNAPSHOT_2026-07-05.md)

---

## Repository sınırı

| Repo | Rol | fair-crm'den erişim |
|------|-----|---------------------|
| **fair-crm** | CRM product service | — |
| **kyrox-core** | Platform (auth, RBAC, audit, org) | HTTP API only |
| **kyrox-platform** | ADR / platform kararları | Dokümantasyon referansı |

Fair CRM **kyrox-core Python kodunu import etmez**. Core değişikliği gerekiyorsa Core repo'da yapılır; Fair CRM sadece public API contract'ını kullanır.

---

## Fair CRM backend yapısı

Modül pattern: `domain → application → infrastructure → api`

```text
backend/app/
├── core/              # config, logging, middleware
├── db/                # SQLAlchemy session, Base
├── integrations/
│   └── kyrox_core/    # Core HTTP adapters (auth, authorization, audit, ...)
├── modules/           # product domain modülleri
│   ├── customers/
│   ├── fairs/
│   ├── imports/
│   ├── contacts/
│   ├── participations/
│   ├── activities/
│   ├── scraper/
│   ├── smtp/
│   ├── system_admin/  # backups, data operations
│   └── data_integration/
└── shared/            # ortak primitifler
```

Tablolar: `crm_*` prefix. `organization_id` logical tenant key (Core FK değil).

---

## Veritabanları

| DB | Schema sahibi | Fair CRM Alembic |
|----|---------------|------------------|
| `fair_crm` | Fair CRM product | `backend/alembic/versions/` |
| `kyrox_core` | KYROX Core | kyrox-core repo (Fair CRM script'leri seed için okur/yazar) |

Restore sonrası **her iki DB için de** `alembic upgrade head` zorunlu (bkz. `.cursor/rules/db-restore-alembic.mdc`).

---

## Auth / RBAC katmanı (tamamlanmış)

| Bileşen | Durum | Konum |
|---------|-------|-------|
| Core permission catalog (40 fair_crm.*) | ✅ | kyrox-core migration `20260701_0026` |
| Nested permission code | ✅ | Core `PermissionCode` |
| Fair CRM endpoint enforcement | ✅ | Modül `dependencies.py` + use case checks |
| Central role matrix | ✅ | `scripts/fair_crm_role_matrix.py` |
| Dev identity seed | ✅ | `scripts/seed_core_dev_identity.py` |
| Prod-path E2E + CI gate | ✅ | `scripts/e2e_validation.py`, `.github/workflows/prod-path-e2e.yml` |
| Dev bypass (local only) | ✅ | `integrations/kyrox_core/dev_bypass.py` |

Detay: [AUTH_RBAC_HANDOVER.md](AUTH_RBAC_HANDOVER.md)

---

## Core entegrasyon yüzeyi

`backend/app/integrations/kyrox_core/`:

| Modül | Port / protokol | Kullanım |
|-------|-----------------|----------|
| `auth.py` | Lokal JWT decode | Her istek |
| `authorization.py` | Core HTTP | Permission check |
| `audit.py` | Core HTTP | Best-effort audit write |
| `settings.py` | Core HTTP | Org settings |
| `jobs.py` | Core HTTP | Background jobs |
| `dev_bypass.py` | Lokal | Dev only — prod-path'te kapalı |

---

## Frontend

- React + TypeScript + Vite (`frontend/src/`)
- API çağrıları: `frontend/src/api/` — browser base: `/api/v1/...` ve `/kyrox-core/api/v1/...` (`VITE_*` boş)
- Görünen etiketler: Türkçe (`frontend/src/labels/`)
- Auth: Core login (`/kyrox-core/...`) → JWT → Fair CRM API (`/api/v1/...`) + `X-Organization-Id`

Org switcher / tam auth UI bu handover kapsamında değil; backend RBAC hattı hazır.

---

## Dev runtime

| Servis | URL (process / UI) |
|--------|---------------------|
| Core (process) | http://127.0.0.1:8000 |
| Fair CRM API (process) | http://127.0.0.1:8001 |
| Fair CRM UI | http://127.0.0.1:5173 |
| Browser → Fair CRM | `/api/v1/...` (Vite/Nginx → 8001) |
| Browser → Core | `/kyrox-core/api/v1/...` (Vite/Nginx → 8000) |
| PostgreSQL | 127.0.0.1:5432 |

Script'ler: `scripts/dev/dev-start.ps1`, `reset-dev.ps1`, `dev-stop.ps1`

Detay: [DEV_RUNTIME.md](DEV_RUNTIME.md), [DEV_RESTART_GUIDE.md](DEV_RESTART_GUIDE.md)

---

## Test piramidi (auth odaklı)

```text
Unit / module pytest (in-memory SQLite, mock auth adapters)
  ├── test_endpoint_permission_enforcement.py
  └── test_role_matrix_authorization.py

Integration / E2E (gerçek Postgres + Core + Fair CRM)
  └── scripts/e2e_validation.py --prod-path

CI
  └── .github/workflows/prod-path-e2e.yml
```

---

## Aktif product alanları (özet)

Tam liste: [PROJECT_STATUS.md](../PROJECT_STATUS.md)

- Customer, Fair, Contact, Participation, Activity modülleri
- Import batch / preview / merge pipeline (devam eden hedefler)
- Scraper + adapter management
- System admin (backups, data operations)
- SMTP modülü
- Linked fairs, run v2 + JSON handoff

---

## Bilinçli olmayan sınırlar

- Fair CRM Core migration'ı yazmaz (permission catalog Core-owned)
- Audit write başarısız olsa CRM mutation fail etmez (best-effort)
- Super-admin bypass Core tarafında ayrı konu; Fair CRM dev bypass'tan farklı
- Production deployment / secrets management bu dokümanda yok

---

## Sonraki mantıklı adımlar (auth dışı)

PROJECT_STATUS ve PRODUCT_VISION'a göre:

- Import batch / preview / duplicate / merge pipeline
- Canonical import schema entegrasyonu
- Frontend auth/org switcher (ürün kararı)

Auth/RBAC altyapısı bu adımlar için hazır; yeni endpoint eklerken permission code + dependency guard pattern'i takip edilmeli.

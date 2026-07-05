# FAIR CRM — Auth / RBAC Handover

**Amaç:** 3 ay sonra veya yeni geliştirici için Fair CRM kimlik doğrulama ve yetkilendirme hattının tek referans özeti.  
**Son güncelleme:** 2026-07-05  
**İlgili:** [INTEGRATION_WITH_CORE.md](INTEGRATION_WITH_CORE.md), [CI_PROD_PATH_E2E.md](CI_PROD_PATH_E2E.md), [KNOWN_DECISIONS.md](KNOWN_DECISIONS.md)

---

## 1. Core ile Fair CRM ilişkisi

Fair CRM ve KYROX Core **ayrı servisler**, **ayrı veritabanları**:

| Bileşen | Port (lokal) | Veritabanı | Sorumluluk |
|---------|--------------|------------|------------|
| KYROX Core | 8000 | `kyrox_core` | Auth, org, membership, RBAC, audit, settings |
| Fair CRM | 8001 | `fair_crm` | CRM domain (`crm_*` tablolar) |

**Entegrasyon kuralı (ADR-007):** Sadece Core **public HTTP API**. Core Python modülü import edilmez, paylaşımlı DB session yok, Core router mount edilmez.

Fair CRM istek akışı:

```text
Client → Bearer JWT (Core'dan) + X-Organization-Id
       → Fair CRM: JWT doğrula (lokal, JWT_SECRET_KEY)
       → Fair CRM: Core authorization/check API ile permission doğrula
       → Use case / route devam veya 403
```

Organization **JWT içinde değil**; tenant bağlamı `X-Organization-Id` header'ından gelir.

---

## 2. Permission catalog — nerede, nasıl çalışır

### Kaynak (Core tarafı)

Product permission kodları **Core veritabanında** `identity_permissions` tablosunda yaşar. Fair CRM migration'ları Core şemasına dokunmaz.

Fair CRM için gerekli Core Alembic migration'ları:

| Revision | İçerik |
|----------|--------|
| `20260701_0025` | İlk `fair_crm.customers.*` izinleri |
| `20260701_0026` | Kalan 38 `fair_crm.*` product izni (toplam 40 fair_crm permission) |

Minimum revision guard: **`20260701_0026`** (seed ve E2E bunu kontrol eder).

### Permission code formatı

Nested segment destekli: `fair_crm.<module>.<action>` (ör. `fair_crm.admin.backups.download`). Core `PermissionCode` value object en az 3 segment kabul eder.

Tam liste: `scripts/fair_crm_role_matrix.py` → `ALL_FAIR_CRM_PERMISSIONS` (40 adet).

### Runtime kontrol

Fair CRM modül dependency'leri (`backend/app/modules/*/api/dependencies.py`):

1. Route seviyesinde `require_read_permission` (ve modüle özel mutation guard'ları)
2. Use case seviyesinde `authorization.check_permission(...)` (create/update/archive vb.)

Core API çağrısı:

```http
POST {CORE}/api/v1/organizations/{org_id}/authorization/check
Authorization: Bearer <token>
X-Organization-Id: <org_id>

{"permission_code": "fair_crm.customers.read"}
```

Adapter: `backend/app/integrations/kyrox_core/authorization.py`

---

## 3. Role matrix — nerede tanımlı

**Tek merkezi kaynak:** `scripts/fair_crm_role_matrix.py`

| Sabit / yapı | Açıklama |
|--------------|----------|
| `ROLE_MATRIX_VERSION` | Matrix sürümü (şu an `1`); seed + E2E doğrular |
| `ROLE_DEFINITIONS` | Rol slug → permission listesi |
| `DEV_ROLE_USERS` | Dev kullanıcı e-posta / UUID eşlemesi |
| `ADMIN_ONLY_PERMISSIONS` | Sadece owner/admin'de olması gereken izinler |

### Roller (dev matrix)

| Rol | Özet yetki |
|-----|------------|
| `owner` | Tüm `fair_crm.*` + `audit.logs.read` |
| `admin` | owner ile aynı |
| `manager` | Operasyonel CRUD; admin/scraper config yok |
| `sales` | Müşteri/contact/participation/activity create/update; admin/scraper run yok |
| `viewer` | Sadece read |
| `scraper_operator` | Fairs read + scraper read/run/download |
| `member` | Legacy Core rolü; Fair CRM izni yok |

Matrix değişikliği yapılacaksa: önce `fair_crm_role_matrix.py`, sonra seed yeniden çalıştır, `ROLE_MATRIX_VERSION` artır.

---

## 4. Dev seed — ne üretir

**Script:** `scripts/seed_core_dev_identity.py`  
**Hedef:** Core DB (`kyrox_core`) — Fair CRM DB'ye yazmaz.

Seed idempotent çalışır (`ON CONFLICT DO NOTHING`).

### Üretilen kayıtlar

1. **Role templates** (`identity_roles`, scope=`organization`): owner, admin, manager, sales, viewer, scraper_operator, member
2. **Role-permission mappings** (`identity_role_permissions`) — matrix'e göre
3. **Dev organization** — varsayılan ID `00000000-0000-4000-8000-000000000010`, slug `fair-crm-dev`
4. **Organization role bindings** (`identity_organization_roles`)
5. **Dev users** + **memberships** + **user role assignments** (`identity_user_roles`)

### Dev kullanıcılar (şifre: `DevPassword123!`)

| Rol | E-posta |
|-----|---------|
| owner | dev@example.com |
| admin | dev-admin@example.com |
| manager | dev-manager@example.com |
| sales | dev-sales@example.com |
| viewer | dev-viewer@example.com |
| scraper_operator | dev-scraper@example.com |

Çalıştırma:

```powershell
python scripts/seed_core_dev_identity.py
```

---

## 5. `.dev_state.json` — ne işe yarar

**Konum:** `scripts/.dev_state.json` (gitignore — commit edilmez)

Seed tamamlandığında yazılır. E2E ve manuel testler bu dosyayı okur.

### Örnek alanlar

```json
{
  "email": "dev@example.com",
  "password": "DevPassword123!",
  "user_id": "...",
  "organization_id": "00000000-0000-4000-8000-000000000010",
  "fair_crm_permission_count": 40,
  "role_matrix_version": 1,
  "roles": {
    "owner": { "email": "...", "user_id": "...", "organization_role_id": "..." },
    ...
  }
}
```

**Kullanım alanları:**

- E2E login (owner credentials)
- Role bazlı live auth testleri (14b)
- SQL RBAC chain doğrulama (user_id + org_id + role slug)
- Stale seed tespiti (`role_matrix_version`, eksik roller)

Dosya yoksa veya sürüm uyumsuzsa: `python scripts/seed_core_dev_identity.py`

---

## 6. Prod-path E2E ve CI gate

**Ana script:** `scripts/e2e_validation.py`  
**Modlar:** `--prod-path` veya `--ci` (aynı davranış)

Prod-path gate şunları doğrular:

- Env + live bypass kapalı
- Core migration >= `20260701_0026`
- Seed + idempotency + role matrix SQL
- Pytest: endpoint permission + role matrix
- Live JWT auth, foreign org, scope mismatch
- Role bazlı selective auth (viewer/sales/scraper_operator/owner/admin)
- Customer flow (adım 15–19)

**Wrapper:** `scripts/run-prod-path-e2e.ps1`  
**CI workflow:** `.github/workflows/prod-path-e2e.yml`  
**Detay:** [CI_PROD_PATH_E2E.md](CI_PROD_PATH_E2E.md)

Rapor: `scripts/e2e_validation_report.json`

---

## 7. Dev bypass — nedir, prod-path'te neden kapalı

**Amaç:** Core ayakta değilken veya hızlı UI geliştirmede Fair CRM'yi tek başına çalıştırmak.

**Konfig:** `backend/.env`

```env
FAIR_CRM_DEV_BYPASS_CORE=false   # prod-path için zorunlu
FAIR_CRM_DEV_BYPASS_TOKEN=dev-bypass
APP_ENV=development              # bypass sadece development/local/test'te izinli
```

**Davranış (`backend/app/integrations/kyrox_core/dev_bypass.py`):**

- `Authorization: Bearer dev-bypass` → Core authorization atlanır, tüm permission'lar allow
- Audit write no-op olabilir
- Gerçek JWT doğrulaması bypass edilmez (token geçerliyse normal prod-path)

**Prod-path'te kapalı olmalı çünkü:**

- Bypass açıkken auth/RBAC testleri anlamsız geçer veya yanlış güven verir
- CI gate `Bearer dev-bypass` ile 200 alırsa **bilerek fail eder** (adım 0b / 9b)
- Production'a yakın davranış = gerçek JWT + Core authorization check

---

## 8. Güvenlik hattını doğrulayan testler

| Test | Dosya | Ne doğrular |
|------|-------|-------------|
| Endpoint permission enforcement | `backend/tests/modules/test_endpoint_permission_enforcement.py` | Modül route'larında permission guard; dev-bypass reddi; foreign org |
| Role matrix authorization | `backend/tests/modules/test_role_matrix_authorization.py` | Matrix'e göre allowed/denied; owner full access; admin-only izinler |
| Prod-path E2E (live) | `scripts/e2e_validation.py --prod-path` | Seed, SQL RBAC chain, Core API check, live role auth, customer flow |
| CI gate | `.github/workflows/prod-path-e2e.yml` | Yukarıdakinin otomatik tekrarı |

Pytest çalıştırma (Core/Fair servis gerekmez):

```powershell
cd backend
python -m pytest tests/modules/test_endpoint_permission_enforcement.py tests/modules/test_role_matrix_authorization.py -q
```

---

## 9. RBAC zinciri (Core DB)

Seed sonrası bir kullanıcının izni şu zincirden gelir:

```text
identity_user_roles
  → identity_organization_roles
    → identity_roles (role template, slug=owner|admin|...)
      → identity_role_permissions
        → identity_permissions (code=fair_crm.*)
```

E2E adım 11b / 11f bu zinciri SQL ile doğrular.

---

## 10. Hızlı troubleshooting

| Belirti | Kontrol |
|---------|---------|
| 403 tüm endpoint'lerde | Seed çalıştı mı? Owner user doğru org'da mı? |
| 401 | JWT_SECRET_KEY Core ile eşleşiyor mu? |
| E2E 0b fail | Fair CRM bypass açık — `reset-dev.ps1`, `.env` false |
| E2E 3b fail | `cd kyrox-core && python -m alembic upgrade head` |
| E2E 11 fail | `python scripts/seed_core_dev_identity.py` |
| Matrix değişti ama auth eski | Seed + `ROLE_MATRIX_VERSION` artır |

---

## Okuma sırası (yeni geliştirici)

1. Bu dosya
2. [DEV_RESTART_GUIDE.md](DEV_RESTART_GUIDE.md) — makineyi ayağa kaldır
3. [PROJECT_SNAPSHOT_2026-07-05.md](PROJECT_SNAPSHOT_2026-07-05.md) — o günkü durum
4. [INTEGRATION_WITH_CORE.md](INTEGRATION_WITH_CORE.md) — API detayları
5. [CI_PROD_PATH_E2E.md](CI_PROD_PATH_E2E.md) — gate çalıştırma

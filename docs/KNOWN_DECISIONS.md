# FAIR CRM — Known Decisions

**Amaç:** Kritik mimari kararlar ve dokunulmaması gereken alanlar — regresyon ve boundary ihlallerini önlemek.  
**Son güncelleme:** 2026-07-05  
**Tam ADR kaydı:** [DECISIONS.md](DECISIONS.md) · **Anayasa:** [PROJECT_CONSTITUTION.md](../PROJECT_CONSTITUTION.md)

---

## 1. Platform sınırı (ADR-007)

| Karar | Uygulama |
|-------|----------|
| Core = platform, Fair CRM = product | Auth, RBAC catalog, audit write API Core'da |
| Entegrasyon sadece HTTP | `backend/app/integrations/kyrox_core/` |
| Ayrı veritabanları | `kyrox_core` vs `fair_crm` |
| `organization_id` logical key | Core FK yok, her sorguda org scope |

**Dokunma:** Fair CRM'den Core Python import, shared session, cross-repo FK **yasak**.

---

## 2. Permission catalog sahipliği

| Karar | Detay |
|-------|-------|
| Product permission'lar Core migration ile seed | kyrox-core `20260701_0025`, `20260701_0026` |
| Fair CRM Alembic Core şemasına yazmaz | Seed script Core DB'ye doğrudan SQL (dev only) |
| Yeni permission önce Core'da | Sonra Fair CRM route guard + matrix |

**Dokunma:** Permission'ı sadece Fair CRM tarafında "tanımlamak" — Core catalog olmadan production'da 403/500.

---

## 3. Role matrix merkezileştirme

| Karar | Detay |
|-------|-------|
| Tek kaynak: `scripts/fair_crm_role_matrix.py` | Seed ve testler buradan import eder |
| `ROLE_MATRIX_VERSION` artırılır | Matrix değişince seed + E2E guard |
| Dev seed idempotent | `ON CONFLICT DO NOTHING` |

**Dokunma:** Role permission'larını seed script içine hard-code etmek — matrix dosyasını bypass eder.

---

## 4. Endpoint authorization pattern

| Karar | Detay |
|-------|-------|
| Route-level read guard | `require_read_permission` dependency |
| Mutation guard use case'te | create/update/archive permission check |
| Scraper / admin tam route guard | run, backup, data ops |
| Dev bypass prod-path'te kapalı | CI gate live probe |

**Dokunma:** Yeni endpoint eklerken permission check atlamak; "AllowAll" adapter'ı prod koduna taşımak.

---

## 5. Dev bypass

| Karar | Detay |
|-------|-------|
| Sadece `APP_ENV` ∈ development/local/test | Production'da RuntimeError |
| Token: `dev-bypass` (configurable) | Core auth/audit atlanır |
| Prod-path E2E bypass'ı reddetmeli | 0b / 9b adımları |

**Dokunma:** CI veya prod-path testlerde bypass'ı açık bırakmak; E2E guard'larını kaldırmak.

---

## 6. Audit writes

| Karar | Detay |
|-------|-------|
| Core audit API best-effort | CRM mutation audit fail'de rollback yok |
| Owner role: `audit.logs.read` | E2E adım 19 audit query |

---

## 7. Import / scraper / merge

| Karar | Detay |
|-------|-------|
| Preview-first import | Doğrudan CRM write yok |
| Human approval zorunlu | Import apply pipeline |
| Scraper logic adapter'da | Import engine'de site-specific kod yok |
| Hall/stand participation'da | Customer aggregate'te değil |

**Dokunma:** Import Preview, Merge Engine, Adapter Builder — kullanıcı açıkça istemedikçe.

---

## 8. Frontend kuralları

| Karar | Detay |
|-------|-------|
| API/ route İngilizce | Label Türkçe |
| Server-side pagination zorunlu | List ekranları |
| Actions column sortable değil | Diğer kolonlar sortable |

---

## 9. Test ve CI kararları

| Karar | Detay |
|-------|-------|
| Permission pytest servis gerektirmez | In-memory DB + mock auth |
| Prod-path E2E servis gerektirir | Core + Fair + Postgres |
| `--prod-path` = `--ci` | Aynı fail-fast davranış |
| Customer flow 15–19 korunur | E2E regression |

**Dokunma:** `test_endpoint_permission_enforcement.py` ve `test_role_matrix_authorization.py` silmek veya CI'dan çıkarmak.

---

## 10. DB restore kuralı

Restore sonrası **mutlaka**:

```powershell
python -m alembic upgrade head   # fair-crm root
.\scripts\dev\reset-dev.ps1
```

`/health` 200 schema drift'i gizler (ör. admin backups 500).

Kaynak: `.cursor/rules/db-restore-alembic.mdc`

---

## Dokunulmaması gereken alanlar (özet)

| Alan | Neden |
|------|-------|
| `kyrox-core` repo (fair-crm'den) | Boundary ihlali |
| Core permission migration'ları (Fair CRM task'ında) | Platform owned |
| Import Preview / Merge Engine davranışı | Stabilize edilmiş pipeline |
| `fair_crm_role_matrix.py` bypass etmeden rol değiştirme | Seed/test drift |
| Prod-path E2E bypass guard'ları | Güvenlik gate |
| Super-admin bypass (Core) | Platform davranışı |

---

## Bilinçli trade-off'lar

| Konu | Seçim | Gerekçe |
|------|-------|---------|
| JWT local validate | Core introspection yerine shared secret | Latency, Sprint 1 basitliği |
| Dev seed raw SQL | Core admin API yerine | Dev-only, idempotent, hızlı |
| Audit best-effort | Strong consistency yerine | CRM availability öncelik |
| Bypass ayrı prod-path gate | Her dev'de Core zorunlu değil | UI geliştirme hızı vs CI doğrulama |

---

## Karar değiştirilecekse

1. [DECISIONS.md](DECISIONS.md)'e yeni ADR veya güncelleme
2. Matrix/seed/E2E/test senkron güncelleme
3. [PROJECT_STATUS.md](../PROJECT_STATUS.md) ve gerekirse yeni snapshot

---

## İlgili dokümanlar

- [AUTH_RBAC_HANDOVER.md](AUTH_RBAC_HANDOVER.md)
- [ARCHITECTURE_STATUS.md](ARCHITECTURE_STATUS.md)
- [INTEGRATION_WITH_CORE.md](INTEGRATION_WITH_CORE.md)
- [PROJECT_SNAPSHOT_2026-07-05.md](PROJECT_SNAPSHOT_2026-07-05.md)

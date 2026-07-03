# Internal Customer Cleanup Utility (ADR-030)

**Status:** Accepted — internal maintenance only  
**Date:** 2026-07-03 (revised)  
**Audience:** Operators / platform maintainers — **not** tenant-facing product

---

## 1. Amaç

Mevcut **master DB**'yi **bir defaya mahsus** temizlemek:

1. Duplicate customer gruplarını tespit et
2. Operatör winner/loser seçerek güvenli merge uygula
3. Fair participation geçmişini koru
4. Merge audit bırak
5. Temiz DB backup al

Import Decision flow'a **dokunulmaz**.

---

## 2. Ne değildir

| Çıkarıldı (kapsam dışı) |
|-------------------------|
| Tenant günlük kullanım ekranı |
| Cleanup Queue platformu (`cleanup_batches`, `cleanup_groups`, ADR-029 UI) |
| Suppression / KEEP_SEPARATE kalıcılığı |
| Sürekli data-quality modülü |
| Geniş REST API seti (`/customer-cleanup/*`) |
| Automatic merge |
| Physical delete |
| Merge undo |
| Yeni product permissions |

Bu bir **internal maintenance tool**'dur (CLI / script / tek seferlik operatör akışı).

---

## 3. Kapsamda kalanlar

| Özellik | Açıklama |
|---------|----------|
| **Duplicate scan** | Org genelinde grup üretimi (isim, email, phone, tax, domain, city+fuzzy) |
| **Winner / loser merge** | Operatör onayı; otomatik merge yok |
| **Fair participation preservation** | Kritik güvenlik kuralı — hiçbir fuar katılımı kaybolmaz |
| **Merge event / audit** | Future dedicated audit record + optional Core audit (not implemented) |
| **Loser inactive** | `inactive` + merge link alanları |
| **Optional inactive soft delete** | Temizlik sonrası operatör pasif kayıtları toplu soft-delete edebilir |

---

## 4. Operatör akışı (tek seferlik)

```text
1. backup-db.ps1          → mevcut DB yedeği
2. cleanup scan           → duplicate_groups.json (veya benzeri rapor)
3. operatör inceleme      → winner seçimi, merge planı onayı
4. cleanup apply          → merge transaction'ları (dry-run destekli)
5. doğrulama              → participation sayıları, spot check
6. [opsiyonel] inactive soft delete
7. backup-db.ps1          → temiz DB yedeği
```

Araç konumu (öneri): `scripts/maintenance/customer_cleanup/` — Python CLI, mevcut `app` domain/use-case'leri paylaşır.

---

## 5. Zorunlu merge kuralları

### 5.1 Fair participation (kritik)

> Customer duplicate merge hiçbir fuar katılım bilgisini kaybettiremez.

| Adım | Kural |
|------|--------|
| 1 | Winner belirlenir |
| 2 | Loser'ın tüm participation'ları alınır |
| 3 | Winner'da aynı `fair_id` var mı? |
| 4 | Yoksa → participation winner'a **taşınır** |
| 5 | Varsa → duplicate oluşturulmaz; winner kaydı korunur |
| 6 | Winner boş alanlar loser'dan doldurulabilir |
| 7 | Çakışan alanlar winner'da kalır; `conflicts[]` audit'e yazılır |
| 8 | Loser participation soft-deactivate (veri winner'da güvende) |
| 9 | Loser customer `inactive` + merge link alanları |
| 10 | Tek transaction |

### 5.2 Notes / serbest metin

- `description`, participation `notes` → **otomatik birleştirilmez**
- Winner metni korunur
- Loser metni yalnızca merge event snapshot'ında

### 5.3 Loser customer durumu (MERGED enum yok)

| Alan | Değer |
|------|--------|
| `status` | `inactive` |
| `merged_into_customer_id` | winner UUID |
| `merged_at` | timestamptz |
| `merged_by_user_id` | operatör / system user UUID |

### 5.4 Güvenlik

- Merge **asla** physical delete yapmaz
- Winner aktif kalır
- Operatör sonradan inactive kayıtları soft-delete edebilir (opsiyonel adım)

### 5.5 Opsiyonel inactive soft delete

Yalnızca maintenance aracı üzerinden, `status = inactive` kayıtlar için:

- `status = deleted`
- `deleted_at = now()`
- `deleted_by_user_id` set
- `merged_into_customer_id` ve merge history **korunur**
- Participations, contacts, activities, import history **korunur**

---

## 6. Database / code status

**Not implemented.** No migration `0016`, no cleanup/suppression tables, no `crm_customers` merge or delete columns, no merge event table, no maintenance CLI.

When implementation is scoped, schema and tooling will be added in a separate change. Until then this document records decisions only.

**Explicitly out of scope for now:**

- `crm_customer_cleanup_batches`, `crm_customer_cleanup_groups`, `crm_customer_cleanup_suppressions`
- Tenant-facing Cleanup Queue (ADR-029 import decision UI remains separate)
- `CustomerStatus.deleted` / `CustomerStatus.merged`

**Future option:** Excel Import-like review UI for operator merge review (not committed).

### 6.1 Uygulama kodu (gelecek)

| Bileşen | Konum (öneri) |
|---------|----------------|
| `DuplicateGroupScanner` | `app/modules/customers/maintenance/` veya `scripts/...` |
| `MergeCustomersUseCase` | Domain use case; import matcher reuse |
| CLI `scan` / `apply` / `soft-delete-inactive` | `scripts/maintenance/customer_cleanup/` |

Product API, frontend route, permission **eklenmez**.

---

## 7. Duplicate scan (internal)

Mevcut import matcher'ları **read-only reuse**:

- `company_name_normalizer`, `company_name_matcher`
- Union-find grouping: tax_number, email, phone, website domain, normalized_name, fuzzy name, city+name

Çıktı: JSON rapor — grup ID, üyeler, sinyaller, önerilen winner. Operatör düzenler; `apply` input'u bu plandan okunur.

---

## 8. Mevcut şema ile ilişki

| Mevcut | Cleanup sonrası |
|--------|-----------------|
| `crm_customers` | Winner aktif; loser `inactive` + merge link |
| `crm_customer_fair_participations` | Tüm fuarlar winner altında |
| `crm_contacts`, `crm_activities` | `customer_id` → winner |
| `crm_import_rows` FK'leri | loser referansları → winner |
| `archived` status | Değişmez; ayrı operatör yolu |

---

## 9. Doğrulama checklist (operatör)

- [ ] Pre-cleanup backup alındı
- [ ] Scan raporu incelendi
- [ ] Dry-run apply hatasız
- [ ] Winner participation count ≥ loser + winner öncesi toplam (fair bazında)
- [ ] Merge audit kayıtları oluştu (when implemented)
- [ ] Post-cleanup backup alındı

---

## 10. İlgili ADR'ler

| ADR | İlişki |
|-----|--------|
| ADR-005 / 016 | Import flow dokunulmaz |
| ADR-020 | Physical delete yok; maintenance soft delete |
| ADR-029 | **Uygulanmaz** — tenant Decision Queue yok |
| ADR-030 | Bu doküman |

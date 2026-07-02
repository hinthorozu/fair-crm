# UMCRM Legacy Migration Cleanup — Completion Report

Generated: 2026-07-02

## Temizlenen DB kapsamı

Dev organization (`00000000-0000-4000-8000-000000000010`) domain tabloları `migrate_umcrm_to_kyrox.py --apply` öncesi otomatik reset ile temizlendi:

| Tablo | İşlem |
|-------|--------|
| `crm_activities` | TRUNCATE (org scoped) |
| `crm_customer_fair_participations` | TRUNCATE |
| `crm_contacts` | TRUNCATE |
| `crm_import_rows` / `crm_import_batches` | TRUNCATE |
| `crm_customers` | TRUNCATE |
| `crm_fairs` | TRUNCATE |

**Korunan:** Alembic migration history, users, roles, organizations, KYROX Core tabloları, schema.

## Kullanılan SQL dosyası

`c:\Users\hinthorozu\Desktop\withdata_u7409970_umycrm.sql`

- 29,321 company
- 40,240 companyemail
- 115 fair
- 29,562 fairtocompany relation

## Değişen migration/parser dosyaları

| Dosya | Değişiklik |
|-------|------------|
| `scripts/legacy/umcrm_cleaning.py` | `classify_contact_token`, `parse_company_contact_slots`, `sanitize_user_notes`, country text detection |
| `scripts/legacy/umcrm_sql_parser.py` | Kolon 2–6 semantik sınıflandırma (phone/web/email/country); `inline_emails` |
| `scripts/legacy/clean_umcrm_dump.py` | Inline email merge, `additional_phones`, sanitized notes |
| `scripts/legacy/umcrm_migration_engine.py` | Description = yalnızca kullanıcı notları; metadata report alanları; temiz activity/participation notes |
| `scripts/legacy/migrate_umcrm_to_kyrox.py` | `umcrm_migration_customer_metadata.json` raporu |
| `scripts/legacy/tests/test_umcrm_sql_parser.py` | Yeni parser testleri |
| `scripts/legacy/tests/test_clean_umcrm_dump.py` | Domain/website testleri |
| `scripts/legacy/tests/test_migrate_umcrm_to_kyrox.py` | Description metadata exclusion testi |

## Website regex yaklaşımı

- `is_valid_website()` mevcut `normalize_website_host()` + `urlparse` kullanır.
- `http://` / `https://` zorunlu değil; `example.com`, `www.example.com`, `example.com.tr` kabul edilir.
- Şema yoksa `normalize_website_url()` `https://` ekler.
- Email/telefon benzeri değerler website olarak sınıflandırılmaz.
- Ülke metni (`Türkiye` vb.) website olarak alınmaz.

## Phone / email mapping yaklaşımı

**Parser:** Kolon 2–6 her değer `classify_contact_token()` ile phone / website / email / country olarak ayrılır. Eski şema (phone1, phone2) ve yeni şema (country, phone, website) aynı kod yolunda işlenir.

**Phone:** Temizlenmiş telefonlar `phone_values_clean` listesinde tutulur. Birincil telefon `customer.phone`; ek telefonlar `additional_phones` (migration metadata raporu, description değil).

**Email:** `companyemail` tablosu + inline slot emailler birleştirilir. `customer.email` alanına yazılır; 255 karakter taşması `additional_emails` metadata raporunda.

## Description cleanup yaklaşımı

`customer.description` artık yalnızca `notes_clean` (gerçek kullanıcı notları, sanitize edilmiş).

**Description'dan kaldırılanlar:**
- Legacy company ID
- Migration review status
- Additional phones / emails etiketleri
- Merge group / alias / phone review flag metinleri

**Metadata konumu:** `migration_reports/umcrm_migration_customer_metadata.json` (legacy ID, review status, additional phones/emails, merge group).

**Activity:** `"Imported from legacy UMCRM."` — teknik metadata yok.

## Re-import edilen kayıt sayıları

| Entity | Oluşturulan |
|--------|-------------|
| Fairs | 115 |
| Customers | 28,155 |
| Participations | 29,561 |
| Activities | 28,155 |

Apply stats: `failed_records: []` (sıfır hata).

## Örnek doğrulama kayıtları

### ACEMOĞLU GIDA SANAYİ VE TİCARET LTD. ŞTİ. (legacy ID 18486)

| Alan | Değer |
|------|-------|
| KYROX customer ID | `1db06450-ba6a-586c-8e81-3c7875adbdac` |
| phone | `903423379340` (CRM `normalize_phone` — kaynak: `3423379340`) |
| email | `info@oncusalca.com.tr` |
| website | `oncusalca.com.tr` |
| description | `null` (temiz) |

Cleaned JSON (önce/sonra):

- **Önce:** `phone_values_clean: ["Türkiye", "3423379340", "oncusalca.com.tr"]`, `website_values_clean: []`
- **Sonra:** `phone_values_clean: ["3423379340"]`, `website_values_clean: ["https://oncusalca.com.tr"]`

### Eski şema örneği (company ID 1)

- phone1=`8508000294`, phone2=`2322576940` — doğru phone slotlarına map edildi.

## Test sonuçları

| Suite | Sonuç |
|-------|-------|
| Legacy scripts (`scripts/legacy/tests/`) | **48 passed** |
| Backend (`backend/tests/`) | **259 passed**, 1 failed |
| Frontend build | **PASS** |

**Bilinen backend failure (önceden var):** `test_data_integration_api.py::test_apply_job_completes` — import engine apply job testi; bu migration cleanup kapsamı dışında.

## Bilinen limitler

1. **Çoklu telefon:** CRM'de multi-phone modeli yok; ikinci+ telefonlar yalnızca migration metadata raporunda.
2. **Çoklu email taşması:** 255 karakter üstü `;` ayrılmış emailler metadata raporunda; customer.email truncate edilir.
3. **Telefon normalizasyonu:** Backend `normalize_phone()` Türkiye numaralarına `90` öneki ekleyebilir (ör. `3423379340` → `903423379340`).
4. **Website storage:** DB'de şemasız domain saklanabilir (`oncusalca.com.tr`); clean aşamasında `https://` eklenir.
5. **Merge plan:** Mevcut `merge_plan/*.json` yeniden üretilmedi; isim/email tabanlı plan aynı kaldı. Contact field düzeltmesi merge kararlarını etkilemez.
6. **10 haneli VKN/tax:** Sayısal 10 haneli değerler phone olarak sınıflandırılabilir (legacy veri belirsizliği).

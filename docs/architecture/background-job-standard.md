# FAIR CRM Background Job Standard

## Amaç

FAIR CRM içinde uzun süren tüm arka plan işlerinin ortak bir standartla yönetilmesi.

Bu standart şu tip işler için geçerlidir:

- Müşteri İletişim Zenginleştirme
- Scraper run
- Import analyze / merge analyze
- Duplicate Customer Analysis
- Customers Without Fair Analysis
- Data Operations
- Backup
- Mail gönderimi / toplu mail operasyonları
- DB bakım / analiz işleri

Amaç:

- İşin başlatıldığını görmek
- Canlı ilerlemeyi takip etmek
- Logları izlemek
- Yanlış başlatılan işi durdurmak
- İşin completed / failed / cancelled durumuna net kapanmasını sağlamak
- Running’de sonsuza kadar kalan işleri engellemek

---

## 1. Ortak Job Yaşam Döngüsü

Her uzun iş aşağıdaki status modelini desteklemelidir:

```text
queued
running
cancel_requested
cancelling
cancelled
completed
failed
```

### Status anlamları

```text
queued
İş sıraya alındı, henüz başlamadı.

running
İş aktif olarak çalışıyor.

cancel_requested
Kullanıcı işi durdurmak istedi.

cancelling
Worker iptal isteğini gördü ve güvenli duruşa geçiyor.

cancelled
İş kullanıcı isteğiyle iptal edildi.

completed
İş başarıyla tamamlandı.

failed
İş hata ile bitti.
```

### Kritik kural

```text
cancelled != failed
```

İptal edilen iş hata değildir. Kullanıcı kararıdır.

---

## 2. Ortak Job Alanları

Her background job kaydında en az şu alanlar bulunmalıdır:

```text
id
organization_id
job_type
source_module
status
requested_by
cancel_requested_by
cancel_requested_at
started_at
finished_at
duration_ms
progress_current
progress_total
progress_percent
last_heartbeat_at
summary_json
error_message
created_at
updated_at
```

### job_type örnekleri

```text
customer_contact_enrichment
scraper_run
bulk_email_send
database_backup
duplicate_customer_analysis
customers_without_fair_analysis
import_analyze
data_cleanup
```

---

## 3. Ortak Log Standardı

Her job için log tutulmalıdır.

Log alanları:

```text
id
job_id
step
level
message
metadata_json
created_at
```

### level değerleri

```text
debug
info
warning
error
success
```

### Örnek log step değerleri

```text
started
progress
item_started
item_completed
item_failed
cancel_requested
cancelling
cancelled
completed
failed
```

Her modül kendi özel step’lerini ekleyebilir.

Örnek enrichment step’leri:

```text
candidates_query_started
candidates_query_finished
candidate_selected
website_fetch_started
website_fetch_success
website_fetch_failed
contact_extracted
email_found
not_found
handoff_row_created
import_batch_created
run_finished
```

---

## 4. Durdurma / Cancel Standardı

İşler aniden process kill ile durdurulmamalıdır.

Doğru model:

```text
cooperative cancellation
```

Yani:

1. Kullanıcı “Durdur” butonuna basar.
2. Job kaydına `cancel_requested_at` yazılır.
3. Status `cancel_requested` olur.
4. Worker güvenli checkpoint’lerde cancel flag kontrol eder.
5. Cancel isteği varsa status `cancelling` olur.
6. Worker o ana kadarki güvenli çıktıları korur.
7. Status `cancelled` olur.
8. Log’a iptal bilgisi yazılır.

---

## 5. Worker Checkpoint Standardı

Her uzun worker şu pattern’i kullanmalıdır:

```python
for item in items:
    check_cancel_requested(job_id)

    process_item(item)

    update_progress(job_id)

    check_cancel_requested(job_id)
```

Cancel algılanırsa:

```python
mark_cancelling(job_id)
write_log("cancelling", "İş durduruluyor")

# güvenli kapanış
finalize_partial_results()

mark_cancelled(job_id)
write_log("cancelled", "İş kullanıcı tarafından iptal edildi")
return
```

---

## 6. Partial Result Kuralı

İptal edilen işte o ana kadar üretilen güvenli sonuçlar korunmalıdır.

### Enrichment örneği

```text
İşlenen customer state’leri korunur.
pending_merge oluşmuşsa korunur.
email_found / email_not_found / failed state’leri korunur.
Hiç işlenmeyen customer’lara state yazılmaz.
```

### Mail örneği

```text
sent → korunur
failed → korunur
queued → cancelled veya pending kalabilir, modül kararına göre
sending → normalize edilir
```

Aynı mail tekrar gönderilmemelidir.

### Backup örneği

```text
Yarım backup dosyası downloadable görünmemelidir.
Temp dosya temizlenmelidir.
Backup kaydı cancelled olmalıdır.
```

---

## 7. UI Standardı

Run History / Background Jobs ekranında her job için:

```text
İş tipi
Başlatan kullanıcı
Başlangıç zamanı
Durum
İlerleme
Süre
Son log
Detay linki
Durdur butonu
```

Duruma göre buton davranışı:

```text
queued / running
→ Durdur butonu görünür

cancel_requested / cancelling
→ Durduruluyor... görünür, buton disabled

completed / failed / cancelled
→ Durdur butonu görünmez
```

Detay ekranında:

```text
Canlı loglar
Progress
Summary
Error varsa error
Cancel bilgisi
Partial result linkleri
```

---

## 8. Cancel API Standardı

Uzun vadede ortak endpoint tercih edilir:

```http
POST /api/v1/background-jobs/{job_id}/cancel
```

İlk fazda modül bazlı endpoint kabul edilebilir:

```http
POST /api/v1/scraper/runs/{run_id}/cancel
POST /api/v1/mail/operations/{operation_id}/cancel
POST /api/v1/admin/data-operations/{operation_id}/cancel
```

Cancel response örneği:

```json
{
  "job_id": "...",
  "status": "cancel_requested",
  "cancel_requested_at": "...",
  "message": "İptal isteği alındı. İş güvenli noktada durdurulacak."
}
```

---

## 9. Heartbeat / Stuck Job Standardı

Running job’lar düzenli heartbeat yazmalıdır:

```text
last_heartbeat_at
```

Worker belirli aralıklarla bunu günceller.

Örnek:

```text
Her 10-30 saniyede bir heartbeat
```

Maintenance job veya admin script şu kontrolü yapabilir:

```text
status = running
AND last_heartbeat_at eski
→ stale_running
→ failed veya cancelled yapılabilir
```

İlk fazda ayrı `stale_running` status şart değildir; ama tespit mekanizması olmalıdır.

---

## 10. İlk Uygulama Hedefi

İlk iş:

```text
Müşteri İletişim Zenginleştirme run’ları için güvenli iptal/durdurma desteği
```

Sebep:

- Şu an aktif kullanılan uzun iş
- Customer bazlı çalıştığı için checkpoint eklemek kolay
- 30 bin kayıt gibi büyük çalışmalarda yanlış başlatılan işi durdurmak gerekir
- Bu standart oturunca scraper/mail/backup/data operations tarafına yayılabilir

---

## 11. Müşteri İletişim Zenginleştirme Cancel Kuralı

### Beklenen davranış

```text
Run başladı
→ müşteri müşteri işler
→ kullanıcı Durdur dedi
→ worker en yakın customer checkpoint’inde durur
→ işlenen kayıtların sonucu korunur
→ işlenmeyen customer’lara state yazılmaz
→ status = cancelled
```

### Status geçişi

```text
running
→ cancel_requested
→ cancelling
→ cancelled
```

### Loglar

```text
cancel_requested
cancelling
cancelled
```

Metadata’da:

```text
run_id
processed_count
remaining_count
cancel_requested_by
cancel_requested_at
last_processed_customer_id
```

### UI

Run detail ekranında:

```text
Durdur
```

butonu görünür.

Basınca confirmation modal:

```text
Bu çalışmayı durdurmak istediğinize emin misiniz?
İşlenen kayıtlar korunacak, işlenmeyen müşteriler untouched kalacaktır.
```

Başarılı istek sonrası:

```text
Durduruluyor...
```

Run kapanınca:

```text
İptal edildi
```

görünür.

---

## 12. Kabul Kriterleri — İlk Faz

Müşteri İletişim Zenginleştirme için:

- Running run’da Durdur butonu görünür.
- Durdur’a basınca cancel_requested yazılır.
- Worker cancel flag’i görür.
- Worker güvenli noktada durur.
- Status cancelled olur.
- Run History cancelled gösterir.
- Detay ekranında cancelled log’u görünür.
- İşlenen customer sonuçları korunur.
- İşlenmeyen customer’lara state yazılmaz.
- Import batch oluştuysa link korunur.
- Import batch oluşmadıysa normal.
- Cancel edilen iş failed sayılmaz.
- Test eklenir.

---

## 13. Test Planı

### Unit

- cancel_requested status yazılır
- check_cancel_requested true döner
- mark_cancelled doğru çalışır

### Integration

- enrichment run başlatılır
- birkaç customer işlendikten sonra cancel request verilir
- worker durur
- status cancelled olur
- işlenen customer state’leri korunur
- işlenmeyen customer state’i oluşmaz

### UI

- running iken Durdur butonu görünür
- cancel sonrası Durduruluyor görünür
- cancelled sonrası buton kaybolur
- Run History cancelled gösterir

---

## 14. Daha Sonraki Yayılım

Enrichment cancel standardı oturduktan sonra sırayla:

```text
1. Scraper run cancel
2. Mail operation cancel
3. Import analyze cancel
4. Data operations cancel
5. Backup cancel
6. Duplicate analysis cancel
```

Her modülde partial result ve rollback kuralı ayrıca netleştirilecektir.

---

## Karar

Bu standart bundan sonraki uzun süren işler için temel kabul edilecek.

İlk uygulanacak iş:

```text
customer_contact_enrichment cancellation support
```

---

## Uygulama Notu — İlk Faz (2026-07-06)

**İlk uygulama:** `customer_contact_enrichment` cooperative cancellation

**Migration:** `0045_scraper_run_cancellation_fields` (`scraper_run_history` üzerinde cancel/heartbeat/progress alanları); graph birleşimi: `0047_merge_cancellation_and_todo_worklist` (tek head)

**Cancel endpoint:** `POST /api/v1/scraper/runs/{run_id}/cancel`

**Status akışı:** `running` → `cancel_requested` → `cancelling` → `cancelled`

**Kritik kural:** `cancelled` ≠ `failed` — iptal edilen run’da `error_message` null kalır.

**Partial sonuç:** İşlenen müşteri scan state’leri korunur; işlenmeyen müşterilere state yazılmaz. Varsa partial handoff / import batch korunur.

**Kod referansları:**

- `backend/app/modules/scraper/services/scraper_run_cancellation.py` — `RunCancelChecker`
- `backend/app/modules/scraper/services/enrichment_run_executor.py` — customer checkpoint’leri
- `backend/app/modules/scraper/application/enrichment_run_job_runner.py` — `_finalize_cancelled_run`
- `frontend/src/pages/EnrichmentRunDetailPage.tsx` — Durdur butonu ve onay modalı

**Testler:** `backend/tests/modules/scraper/test_enrichment_run_cancellation.py`

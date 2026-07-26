# Provider / MailerSend Kalan İşler

## Mevcut durum

- Generic Provider mimarisi hazır.
- MailerSend adapter hazır.
- Test maili gerçek olarak gönderildi ve ulaştı.

## Kalan işler

### 1. Provider gönderim sonucunu MSO'ya bağlama

Gerçek gönderim sonucundaki aşağıdaki alanların `MailSendOperation` kaydına otomatik yazıldığı doğrulanacak; bağlı değilse bağlanacak:

- `external_message_id`
- `provider_status`

`EmailDeliveryResult` ile MSO `mark_sent(...)` akışı arasındaki bağlantı netleştirilecek.

### 2. MailerSend webhook

MailerSend webhook endpoint'i eklenecek.

Zorunlu konular:

- webhook signature / HMAC doğrulama
- `external_message_id` ile ilgili MSO kaydını bulma
- gelen provider durumunu `provider_status` alanına yazma
- aynı event tekrar gelirse idempotent çalışma

İşlenecek event grupları:

- delivered
- bounce
- opened
- clicked
- complaint
- unsubscribed

### 3. Unsubscribe davranışı

`activity.unsubscribed` geldiğinde:

- gönderilmiş e-posta bir Contact'a aitse ilgili Contact için `email_allowed = false`
- gönderilmiş e-posta doğrudan Customer'a aitse ilgili Customer için `email_allowed = false`
- her iki durumda da Customer kartına aktivite kaydı düşülecek

Aktivite kaydı en az şu bilgileri içerecek:

- işlemin MailerSend unsubscribe webhook'undan geldiği
- ilgili e-posta adresi
- Contact veya Customer seviyesinde hangi iznin kapatıldığı
- tarih/saat
- ilgili MSO / provider message id bağlantısı

### 4. Provider hesabının otomatik pasife alınması

Hata politikası sonucu hesap otomatik pasife alınırsa işlem sessiz kalmayacak.

Kalıcı olarak tutulacak ve UI'da gösterilecek bilgiler:

- pasife alınma nedeni
- provider hata kodu
- provider hata mesajı
- pasife alınma zamanı
- işlemi tetikleyen mail / MSO / batch / operasyon
- otomatik veya manuel pasife alma bilgisi

Kullanıcıya kalıcı bildirim gösterilecek.

Ayrıca hesap pasife alındığında mevcut kuyruktaki maillerin davranışı ayrıca kararlaştırılacak:

- fail
- beklet
- operasyonu durdur
- başka aktif hesaba yönlendir

Bu karar verilmeden varsayım yapılmayacak.

### 5. Retry-After desteği

Provider cevabındaki `Retry-After` değeri alınmış olsa da gecikmeli scheduler henüz yok.

Yapılacaklar:

- `Retry-After` değerini persist etme
- MSO'yu belirtilen zamandan önce tekrar denememe
- mevcut `max_delivery_attempts` sınırını koruma
- worker'ın sürekli aynı kaydı çekmesini önleme

### 6. Küçük batch ile uçtan uca gerçek test

MailerSend hesabıyla küçük bir gerçek toplu gönderim testi yapılacak.

Kontrol edilecekler:

- alıcı çözümleme
- iletişim izni kontrolleri
- MSO oluşturma
- outbox / worker
- MailerSend API gönderimi
- `external_message_id`
- `provider_status`
- retry davranışı
- UI operasyon özeti

### 7. Git / migration / deploy

Tüm provider ve ilgili iletişim izni değişiklikleri tamamlandıktan sonra:

- dirty dosyalar ayrıştırılacak
- yerel/debug dosyalar staging dışında bırakılacak
- migration zinciri doğrulanacak
- test/build çalıştırılacak
- commit/push yapılacak
- deploy sonrası migration ve gerçek gönderim smoke testi yapılacak

Her zaman hariç tutulacak yerel/debug dosyalar:

- `backend/_dump_patches.py`
- `backend/_restore/`
- `frontend/scripts/_dirty_accept_sample.xlsx`

## Durum

Planlandı. Henüz tamamlanmadı.

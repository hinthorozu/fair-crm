# E-Posta ve İletişim Tercihleri Backlog

## Amaç

MailerSend webhook sonuçlarını FAIR CRM içinde işleyerek e-posta adresi ve müşteri seviyesinde iletişim tercihlerini kalıcı olarak yönetmek.

## 1. MailerSend üyelikten çıkma webhook'u

MailerSend'den gelen aşağıdaki event desteklenecek:

```text
activity.unsubscribed
```

Bu event geldiğinde ilgili e-posta adresi bulunacak ve e-posta gönderimine kapatılacak.

## 2. E-posta adresi seviyesinde gönderim izni

E-posta/contact kaydında en az şu bilgiler bulunacak:

```text
send_email = true / false
send_email_reason
```

`activity.unsubscribed` geldiğinde:

```text
send_email = false
send_email_reason = "MailerSend üzerinden üyelikten çıktı"
```

Bu adrese daha sonra toplu veya manuel e-posta gönderilmeyecek.

## 3. Customer seviyesinde iletişim tercihleri

Customer kartında müşterinin iletişim tercihleri yönetilebilecek:

- Telefonla aranmak istiyor mu?
- E-posta almak istiyor mu?

Customer seviyesindeki tercih, bağlı e-posta/contact kayıtlarından önce genel engel olarak değerlendirilecek.

Alanların kesin DB tasarımı uygulama aşamasında mevcut Customer ve Contact modelleri incelenerek belirlenecek.

## 4. Customer pasife alma

Müşteri aranmak veya e-posta almak istemediğinde gerektiğinde pasife alınabilecek.

Pasife alma sırasında:

- Pasife alma nedeni seçilecek veya yazılacak.
- Açıklama/not girilecek.
- İşlem müşteri aktivite/geçmiş kaydına yazılacak.

Örnek:

```text
Durum: Pasif
Neden: İletişim istemiyor
Not: Müşteri aranmak ve e-posta almak istemediğini belirtti.
```

## 5. Gönderim öncesi kontrol sırası

Her e-posta gönderiminden önce aşağıdaki kontroller uygulanacak:

```text
Customer pasif mi?
→ Customer e-posta iletişimine izin veriyor mu?
→ İlgili e-posta/contact kaydında send_email=true mi?
→ Uygunsa gönder
```

Kontroller toplu e-posta, fuar e-postası, manuel görev e-postası ve diğer tüm merkezi mail akışlarında aynı gönderim sınırından uygulanacak.

## 6. Beklenen davranış

- Üyelikten çıkan bir e-posta adresine yeniden mail gönderilmez.
- Bir e-posta adresinin engellenmesi aynı müşterinin diğer izinli adreslerini otomatik olarak engellemez.
- Customer seviyesinde e-posta kapatılırsa müşterinin tüm adreslerine gönderim engellenir.
- Customer pasifse mevcut iş kurallarına göre iletişim aksiyonları engellenir.
- Pasife alma ve iletişim tercihi değişiklikleri geçmişte izlenebilir olur.

## Durum

Planlandı. Henüz implement edilmedi.

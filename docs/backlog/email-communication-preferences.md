# E-Posta ve İletişim Tercihleri Backlog

## Amaç

MailerSend webhook sonuçlarını FAIR CRM içinde işleyerek e-posta adresi ve müşteri seviyesinde iletişim tercihlerini kalıcı olarak yönetmek.

## 1. MailerSend üyelikten çıkma webhook'u

MailerSend'den gelen aşağıdaki event desteklenecek:

```text
activity.unsubscribed
```

Bu event geldiğinde gönderilmiş e-postanın bağlı olduğu kayıt bulunacak ve aşağıdaki kurallar uygulanacak.

### Gönderilmiş e-posta bir Contact kaydına aitse

- İlgili Contact kaydının e-posta iletişim izni `false` yapılacak.
- Yalnızca bu Contact kaydının e-posta gönderimleri engellenecek.
- İşlem ilgili Customer kartına aktivite olarak yazılacak.

### Gönderilmiş e-posta doğrudan bir Customer kaydına aitse

- İlgili Customer kaydının e-posta iletişim izni `false` yapılacak.
- Bu Customer'a bağlı tüm e-posta gönderimleri engellenecek.
- İşlem Customer kartına aktivite olarak yazılacak.

## 2. E-posta adresi / Contact seviyesinde gönderim izni

Contact kaydında mevcut e-posta iletişim izni kullanılacak.

`activity.unsubscribed` geldiğinde ve gönderilmiş e-posta bir Contact kaydına ait olduğunda:

```text
contact.email_permission = false
```

Bu Contact kaydının e-posta adresine daha sonra toplu, manuel veya otomatik hiçbir e-posta gönderilmeyecek.

## 3. Customer seviyesinde iletişim tercihleri

Customer kartındaki mevcut “İletişim İzinleri” bölümü kullanılacak.

Customer kartında müşterinin iletişim tercihleri yönetilebilecek:

- Telefonla aranmak istiyor mu?
- E-posta almak istiyor mu?

`activity.unsubscribed` geldiğinde ve gönderilmiş e-posta doğrudan Customer kaydına ait olduğunda:

```text
customer.email_permission = false
```

Customer seviyesindeki tercih genel engeldir. Customer e-posta izni `false` ise bağlı Contact izinleri `true` olsa bile müşteriye bağlı hiçbir adrese e-posta gönderilmez.

Alanların kesin DB ve API isimleri uygulama aşamasında mevcut Customer ve Contact iletişim izinleri incelenerek belirlenecek. Yeni duplicate izin alanı oluşturulmayacak.

## 4. Customer aktivite kaydı

Her iki unsubscribe senaryosunda da Customer kartına aktivite düşülecek.

Aktivite en az şu bilgileri içerecek:

- İşlem türü: E-posta üyeliğinden çıkma
- Kaynak: MailerSend webhook
- Etkilenen kayıt türü: Customer veya Contact
- Etkilenen e-posta adresi
- Eski ve yeni e-posta izin durumu
- Provider event zamanı
- İlgili MailSendOperation veya provider message ID

Örnek Contact aktivitesi:

```text
MailerSend üyelikten çıkma bildirimi alındı.
Contact e-posta izni kapatıldı.
E-posta: contact@example.com
```

Örnek Customer aktivitesi:

```text
MailerSend üyelikten çıkma bildirimi alındı.
Customer e-posta iletişim izni kapatıldı.
E-posta: customer@example.com
```

## 5. Customer pasife alma

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

## 6. Gönderim öncesi kontrol sırası

Her e-posta gönderiminden önce aşağıdaki kontroller uygulanacak:

```text
Customer pasif mi?
→ Customer e-posta iletişimine izin veriyor mu?
→ İlgili Contact kaydında e-posta izni true mu?
→ Uygunsa gönder
```

Kontroller toplu e-posta, fuar e-postası, manuel görev e-postası ve diğer tüm merkezi mail akışlarında aynı gönderim sınırından uygulanacak.

## 7. Beklenen davranış

- Üyelikten çıkan bir Contact adresine yeniden mail gönderilmez.
- Contact seviyesindeki engel aynı müşterinin diğer izinli Contact adreslerini otomatik olarak engellemez.
- Customer seviyesinde e-posta kapatılırsa müşterinin tüm adreslerine gönderim engellenir.
- Customer pasifse mevcut iş kurallarına göre iletişim aksiyonları engellenir.
- Her unsubscribe işlemi Customer kartı aktivite geçmişinde izlenebilir olur.

## Durum

Planlandı. Henüz implement edilmedi.

# FAIR CRM To-Do Module — Faz 1 Kapsamı

## Amaç

FAIR CRM içinde organizasyon bazlı, bağımsız bir To-Do modülü oluşturulacak.

Bu fazda To-Do kayıtları herhangi bir müşteri, fuar, import, aktivite veya job kaydına bağlı olmayacak. İlk hedef basit görev takibi yapabilmek.

İlerleyen fazlarda bu yapı arama listesi, WhatsApp gönderimi, SMS gönderimi, toplu mail gönderimi, fuar müşteri listeleri ve aktivite bağlantıları için genişletilecek.

---

## Faz 1 Kapsamı

Kullanıcılar organizasyon altında To-Do oluşturabilecek, listeleyebilecek, detayını görebilecek, düzenleyebilecek, tamamlandı yapabilecek ve arşivleyebilecek.

Varsayılan silme davranışı gerçek silme değil, arşivleme olacak.

Gerçek silme işlemi yalnızca admin / owner yetkisine sahip kullanıcılar tarafından yapılabilecek.

---

## To-Do Alanları

### Zorunlu Alanlar

- `organization_id`
- `title`
- `status`
- `priority`
- `category`
- `created_by`

### Opsiyonel Alanlar

- `description`
- `deadline`
- `assignee_user_id`
- `archived_at`
- `completed_at`

### Sistem Alanları

- `id`
- `created_at`
- `updated_at`
- `updated_by`
- `deleted_at` veya gerçek delete kontrolü

---

## Status Değerleri

İlk versiyon için durum değerleri:

- `todo`
- `in_progress`
- `done`
- `cancelled`
- `archived`

---

## Priority Değerleri

İlk versiyon için öncelik değerleri:

- `low`
- `normal`
- `high`
- `urgent`

Varsayılan değer:

- `normal`

---

## Category / Type Değerleri

To-Do kategori listesi aşağıdaki enum değerlerinden oluşacak:

- `arama`
- `toplu_mail`
- `sms`
- `whatsapp`
- `ziyaret`
- `teklif`
- `veri_temizleme`
- `import_kontrol`
- `müşteri_güncelleme`
- `genel_görev`
- `stand_tasarim`
- `diğer`

Varsayılan değer:

- `genel_görev`

---

## Liste Ekranı

To-Do liste ekranında şu alanlar gösterilecek:

- Başlık
- Durum
- Öncelik
- Kategori
- Deadline / son tarih
- Gecikmiş etiketi
- Oluşturan kişi
- Sorumlu kişi
- Güncelleme tarihi

---

## Gecikmiş Etiketi

Deadline tarihi geçmişse ve To-Do tamamlanmamışsa listede `gecikmiş` etiketi gösterilecek.

`done` durumundaki To-Do kayıtları gecikmiş sayılmayacak.

Mantık:

```text
deadline < now AND status != done
```

Bu durumda kayıt listede gecikmiş olarak işaretlenir.

---

## Yetki Mantığı

Minimum permission set:

* `fair_crm.todos.read`
* `fair_crm.todos.create`
* `fair_crm.todos.update`
* `fair_crm.todos.archive`
* `fair_crm.todos.delete`

Davranış:

* To-Do kayıtları organizasyon bazlı tutulacak.
* Kullanıcı sadece yetkili olduğu organizasyonun To-Do kayıtlarını görebilecek.
* Normal silme davranışı archive olacak.
* Gerçek delete sadece admin / owner tarafından yapılabilecek.

---

## API Kapsamı

İlk faz için beklenen endpoint mantığı:

```text
GET    /todos
GET    /todos/{id}
POST   /todos
PATCH  /todos/{id}
POST   /todos/{id}/complete
POST   /todos/{id}/archive
DELETE /todos/{id}
```

### Endpoint Açıklamaları

#### `GET /todos`

To-Do listesini getirir.

Desteklenmesi beklenen filtreler:

* `status`
* `priority`
* `category`
* `assignee_user_id`
* `created_by`
* `is_overdue`
* `include_archived`
* `search`

#### `GET /todos/{id}`

Tek bir To-Do kaydının detayını getirir.

#### `POST /todos`

Yeni To-Do oluşturur.

#### `PATCH /todos/{id}`

Mevcut To-Do kaydını günceller.

#### `POST /todos/{id}/complete`

To-Do kaydını tamamlandı yapar.

Beklenen davranış:

* `status = done`
* `completed_at = now`

#### `POST /todos/{id}/archive`

To-Do kaydını arşivler.

Beklenen davranış:

* `status = archived`
* `archived_at = now`

#### `DELETE /todos/{id}`

Gerçek silme işlemi yapar.

Bu işlem sadece admin / owner yetkisine sahip kullanıcılar için açık olmalıdır.

---

## Filtreler

Liste ekranında ilk faz için desteklenmesi gereken filtreler:

* Durum
* Öncelik
* Kategori
* Sorumlu kişi
* Oluşturan kişi
* Gecikmiş mi?
* Arşivlenenler dahil mi?
* Arama: başlık / açıklama

---

## Kabul Kriterleri

Bu iş aşağıdaki şartlar sağlandığında tamamlanmış sayılır:

1. Organizasyon bazlı To-Do oluşturulabiliyor.
2. To-Do kayıtları organizasyon dışında görünmüyor.
3. Başlık, açıklama, durum, öncelik, deadline, sorumlu kişi ve kategori alanları tutuluyor.
4. Sorumlu kişi alanı boş bırakılabiliyor.
5. Liste ekranında sorumlu kişi görünüyor.
6. Deadline geçmiş ve tamamlanmamış işler `gecikmiş` etiketi alıyor.
7. Normal kullanıcı archive yapabiliyor.
8. Admin / owner gerçek delete yapabiliyor.
9. Kategori listesi belirlenen enum değerleriyle geliyor.
10. CRUD akışı çalışıyor.
11. To-Do şu aşamada müşteri, fuar, import veya aktivite kaydına bağlı değil.

---

## Faz 2'ye Bırakılacaklar

Bu fazda aşağıdaki işler yapılmayacak:

* Fuar listesinden müşteri listesi üretme
* Arama listesi oluşturma
* Liste işlem takibi
* WhatsApp mesaj gönderimi
* Toplu mail gönderimi
* SMS gönderimi
* Aktiviteyle otomatik ilişkilendirme
* Müşteri detayından To-Do güncelleme
* Job / action engine
* To-Do'dan otomatik aksiyon üretme

---

## Özet

İlk uygulama paketi:

```text
FAIR CRM organization-based standalone To-Do module
```

Bu modül şimdilik bağımsız görev takibi sağlar. Gelecek fazlarda liste alma, arama, WhatsApp, SMS, toplu mail ve müşteri aktiviteleriyle ilişkilendirilecek şekilde genişletilecektir.

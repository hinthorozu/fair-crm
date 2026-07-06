# FAIR CRM To-Do Module — Yapılacak İşler

## Amaç

Bu dosya To-Do modülünün teknik yapılacak işlerini takip etmek için oluşturulmuştur.

Bu fazda sadece bağımsız, organizasyon bazlı To-Do modülü yapılacaktır.

---

## Backend İşleri

- [ ] To-Do model / entity tasarla.
- [ ] To-Do tablo migration dosyasını oluştur.
- [ ] `organization_id` zorunlu olacak şekilde organizasyon izolasyonu kur.
- [ ] `title`, `status`, `priority`, `category`, `created_by` alanlarını zorunlu yap.
- [ ] `description`, `deadline`, `assignee_user_id`, `archived_at`, `completed_at` alanlarını opsiyonel yap.
- [ ] Status enum değerlerini ekle:
  - `todo`
  - `in_progress`
  - `done`
  - `cancelled`
  - `archived`
- [ ] Priority enum değerlerini ekle:
  - `low`
  - `normal`
  - `high`
  - `urgent`
- [ ] Category enum değerlerini ekle:
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
- [ ] Varsayılan priority değerini `normal` yap.
- [ ] Varsayılan category değerini `genel_görev` yap.
- [ ] CRUD servislerini yaz.
- [ ] Listeleme endpoint'ine filtreleri ekle:
  - `status`
  - `priority`
  - `category`
  - `assignee_user_id`
  - `created_by`
  - `is_overdue`
  - `include_archived`
  - `search`
- [ ] `complete` aksiyonunu ekle.
- [ ] `archive` aksiyonunu ekle.
- [ ] Admin / owner için gerçek delete davranışını ekle.
- [ ] Normal silme davranışında archive mantığını koru.
- [ ] Overdue / gecikmiş hesaplamasını backend response içinde veya frontend'in hesaplayabileceği şekilde destekle.
- [ ] Permission kontrollerini ekle:
  - `fair_crm.todos.read`
  - `fair_crm.todos.create`
  - `fair_crm.todos.update`
  - `fair_crm.todos.archive`
  - `fair_crm.todos.delete`

---

## API İşleri

- [ ] `GET /todos` endpoint'i.
- [ ] `GET /todos/{id}` endpoint'i.
- [ ] `POST /todos` endpoint'i.
- [ ] `PATCH /todos/{id}` endpoint'i.
- [ ] `POST /todos/{id}/complete` endpoint'i.
- [ ] `POST /todos/{id}/archive` endpoint'i.
- [ ] `DELETE /todos/{id}` endpoint'i.

---

## Frontend İşleri

- [ ] To-Do ana liste ekranı oluştur.
- [ ] Liste ekranında şu kolonları göster:
  - Başlık
  - Durum
  - Öncelik
  - Kategori
  - Deadline / son tarih
  - Gecikmiş etiketi
  - Oluşturan kişi
  - Sorumlu kişi
  - Güncelleme tarihi
- [ ] To-Do oluşturma formu oluştur.
- [ ] To-Do düzenleme formu oluştur.
- [ ] To-Do detay ekranı oluştur.
- [ ] Sorumlu kişi alanını opsiyonel yap.
- [ ] Category dropdown değerlerini ekle.
- [ ] Priority dropdown değerlerini ekle.
- [ ] Status dropdown değerlerini ekle.
- [ ] Deadline geçmiş ve tamamlanmamış işlerde `gecikmiş` etiketi göster.
- [ ] Liste filtrelerini ekle:
  - Durum
  - Öncelik
  - Kategori
  - Sorumlu kişi
  - Oluşturan kişi
  - Gecikmiş mi?
  - Arşivlenenler dahil mi?
  - Arama
- [ ] Tamamlandı yap aksiyonu ekle.
- [ ] Arşivle aksiyonu ekle.
- [ ] Admin / owner kullanıcılar için gerçek delete aksiyonunu göster.
- [ ] Yetkisi olmayan kullanıcıya delete aksiyonunu gösterme.

---

## Test İşleri

- [ ] Organizasyon izolasyonu testi.
- [ ] To-Do oluşturma testi.
- [ ] To-Do listeleme testi.
- [ ] To-Do detay testi.
- [ ] To-Do güncelleme testi.
- [ ] To-Do tamamlandı yapma testi.
- [ ] To-Do arşivleme testi.
- [ ] Admin / owner gerçek delete testi.
- [ ] Yetkisiz delete engelleme testi.
- [ ] Sorumlu kişi boş bırakılabiliyor testi.
- [ ] Deadline geçmiş ve tamamlanmamış kayıt için gecikmiş etiketi testi.
- [ ] `done` durumundaki kayıt için gecikmiş etiketi gösterilmemesi testi.
- [ ] Category enum doğrulama testi.
- [ ] Priority enum doğrulama testi.
- [ ] Status enum doğrulama testi.
- [ ] Liste filtreleri testi.
- [ ] Search testi.

---

## Faz 1 Dışında Bırakılanlar

- [ ] Fuar listesinden müşteri listesi üretme.
- [ ] Arama listesi oluşturma.
- [ ] WhatsApp mesaj gönderimi.
- [ ] SMS gönderimi.
- [ ] Toplu mail gönderimi.
- [ ] Aktivite bağlantısı.
- [ ] Müşteri detayından To-Do güncelleme.
- [ ] Job / action engine.
- [ ] To-Do'dan otomatik aksiyon üretme.

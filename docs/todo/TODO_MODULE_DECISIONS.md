# FAIR CRM To-Do Module — Kararlar

## Alınan Kararlar

### 1. To-Do organizasyon bazlı olacak

To-Do kayıtları kişisel değil, organizasyon bazlı tutulacak.

Kullanıcılar sadece yetkili oldukları organizasyondaki To-Do kayıtlarını görebilecek.

---

### 2. İlk faz bağımsız olacak

İlk fazda To-Do kayıtları müşteri, fuar, import, aktivite veya job kaydına bağlı olmayacak.

Bu bağlantılar sonraki fazlara bırakıldı.

---

### 3. Sorumlu kişi opsiyonel olacak

To-Do kaydında `assignee_user_id` alanı bulunacak ancak zorunlu olmayacak.

Liste ekranında sorumlu kişi gösterilecek.

---

### 4. Silme varsayılan olarak archive olacak

Normal kullanıcı davranışında To-Do gerçek silinmeyecek, arşivlenecek.

Archive için:

- `status = archived`
- `archived_at = now`

---

### 5. Gerçek delete sadece admin / owner yapabilecek

Gerçek silme işlemi sadece admin / owner yetkisine sahip kullanıcılar için açık olacak.

---

### 6. Deadline geçince gecikmiş etiketi gösterilecek

Deadline tarihi geçmiş ve To-Do tamamlanmamışsa listede `gecikmiş` etiketi gösterilecek.

`done` durumundaki kayıtlar gecikmiş sayılmayacak.

---

### 7. İlk fazda category/type alanı olacak

To-Do kayıtlarında kategori alanı bulunacak.

Bu alan ileride arama listesi, WhatsApp gönderimi, SMS gönderimi, toplu mail ve müşteri aktiviteleri gibi aksiyonlara temel hazırlayacak.

---

### 8. Category değerleri

DB/API tarafında ASCII slug kullanılacak. Türkçe karakterli değerler yalnızca frontend UI label olarak gösterilecek (bkz. karar §11).

İlk kategori listesi (slug):

- `arama`
- `toplu_mail`
- `sms`
- `whatsapp`
- `ziyaret`
- `teklif`
- `veri_temizleme`
- `import_kontrol`
- `musteri_guncelleme`
- `genel_gorev`
- `stand_tasarim`
- `diger`

Varsayılan:

- `genel_gorev`

---

### 9. Priority değerleri

İlk priority listesi:

- `low`
- `normal`
- `high`
- `urgent`

Varsayılan:

- `normal`

---

### 10. Status değerleri

İlk status listesi:

- `todo`
- `in_progress`
- `done`
- `cancelled`
- `archived`

---

### 11. Category slug'ları DB/API'de ASCII olacak

Category değerleri veritabanı ve API sözleşmesinde ASCII slug olarak saklanır ve taşınır:

- `arama`
- `toplu_mail`
- `sms`
- `whatsapp`
- `ziyaret`
- `teklif`
- `veri_temizleme`
- `import_kontrol`
- `musteri_guncelleme`
- `genel_gorev`
- `stand_tasarim`
- `diger`

Türkçe karakterli gösterimler (ör. “Müşteri Güncelleme”, “Genel Görev”, “Diğer”) yalnızca frontend label katmanında (`labels/todoLabels.ts`) kullanılır. Encoding, URL filtreleme ve enum doğrulama risklerini önlemek için backend slug listesi Unicode varyantları kabul etmez.

---

### 12. Assignee / creator isim gösterimi Faz 1'de genişletilmeyecek

Backend yalnızca `assignee_user_id`, `created_by`, `updated_by` UUID alanlarını saklar; response'ta isim zorunlu değildir.

Frontend:

- Mevcut kullanıcı veya uygulama içi üyelik datası varsa isim gösterebilir.
- Yoksa UUID veya boş gösterim kabul edilir.

Core org-members entegrasyonu (org üye listesi, display name lookup) Faz 1 kapsamı dışında ayrı iş olarak kalır.

---

### 13. Delete ve archive permission rol dağılımı

| Permission | owner | admin | manager | sales | viewer |
|------------|:-----:|:-----:|:-------:|:-----:|:------:|
| `fair_crm.todos.read` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `fair_crm.todos.create` | ✓ | ✓ | ✓ | ✓ | — |
| `fair_crm.todos.update` | ✓ | ✓ | ✓ | ✓ | — |
| `fair_crm.todos.archive` | ✓ | ✓ | ✓ | ✓ | — |
| `fair_crm.todos.delete` | ✓ | ✓ | — | — | — |

- **Delete** (`DELETE /todos/{id}`): yalnızca owner ve admin (`fair_crm.todos.delete`).
- **Archive**: owner, admin, manager, sales (`fair_crm.todos.archive`); normal “sil” UX'i archive akışına yönlendirilir.
- **Viewer**: yalnızca read; create, update, archive ve delete yetkisi yok.

`scripts/fair_crm_role_matrix.py` bu dağılıma göre güncellenecek.

---

## Sonraki Faz Notları

İleride bu To-Do yapısından aşağıdaki iş akışlarına geçilecek:

- Fuar bazlı müşteri arama listesi üretme
- Arama işlem listesi
- WhatsApp mesaj gönderimi
- SMS gönderimi
- Toplu mail gönderimi
- Aktivite takibi
- Müşteri detay ekranından To-Do / aksiyon güncelleme
- Job / action engine

Örnek gelecek kullanım:

```text
Bugün Intermob fuarındaki müşteriler aranacak.
```

Sistem daha sonra Intermob fuarına bağlı müşteri listesini çıkaracak, kullanıcı arama yaptıkça liste ilerleme durumunu güncelleyecek.

---

## Proje Takip Dosyası Notu

`FAIR_CRM_PROJECT.xlsx` dosyası bulunamadı veya güncellenemedi.

Bu nedenle To-Do modülü kapsamı ve kararları şimdilik repo içindeki aşağıdaki dosyalarda takip ediliyor:

- `docs/todo/TODO_MODULE_SCOPE.md`
- `docs/todo/TODO_MODULE_TASKS.md`
- `docs/todo/TODO_MODULE_DECISIONS.md`

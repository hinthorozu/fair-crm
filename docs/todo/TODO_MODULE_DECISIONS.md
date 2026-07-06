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

İlk kategori listesi:

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

Varsayılan:

- `genel_görev`

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

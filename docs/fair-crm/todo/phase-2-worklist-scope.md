# FAIR CRM Görevler / To-Do Faz 2 — Worklist Scope & Roadmap

## Doküman amacı

Bu doküman, FAIR CRM Görevler / To-Do modülü Faz 2 kapsamını netleştirmek ve ileride aynı yerden devam edebilmek için hazırlanmıştır.

Faz 1 tamamlandı. Faz 2 konusu:

> Görevten müşteri bazlı çalışma listesi oluşturma.

Örnek senaryo:

> "Foodist fuarına katılan tüm müşteriler aranacak" görevi açılır.  
> Sistem Foodist fuarına katılan müşterilerden dinamik çalışma listesi oluşturur.  
> Kullanıcı liste üzerinden müşterileri arar, aktivite girer, sonuç seçer ve satır durumu otomatik güncellenir.

---

## Faz 1 kapanış commitleri

- `41f5154` docs: add organization-based todo module scope
- `752126b` docs: add todo implementation plan and decisions
- `9a375bc` feat: add todo backend crud foundation
- `484c479` feat: add todo actions filters and role matrix
- `e389458` feat: add todo frontend page and navigation
- `646cc29` docs: mark todo phase 1 complete

---

# 1. Netleşmiş kararlar

## 1.1 Çalışma listesi hedefi

Faz 2'de çalışma listesi sadece **müşteri bazlı** olacak.

Kapsam dışı:

- kişi bazlı çalışma listesi
- lead bazlı çalışma listesi
- katılımcı kişi bazlı çalışma listesi

İleride genişletilebilir, fakat Faz 2 için hedef müşteri olacaktır.

---

## 1.2 Liste kaynağı

Liste, müşteri-fuar katılım ilişkisinden üretilecek.

Örnek:

> Foodist fuarına bağlı müşteriler → görev çalışma listesi

Ana kaynak import batch olmayacak. Kaynak, müşteri-fuar ilişkisi / fair participation ilişkisi olacaktır.

---

## 1.3 Liste tipi

Çalışma listesi **dinamik** olacak.

Kurallar:

- Görev açıldığında Foodist'e bağlı 248 müşteri varsa listede 248 müşteri görünür.
- Foodist'e sonradan yeni müşteri eklenirse otomatik olarak görev çalışma listesine girer.
- Liste fiziksel olarak tamamen sabit snapshot olmayacak.
- Buna rağmen her müşteri için görev bazlı satır durumu/state tutulmalıdır.

Not:

> Liste dinamik olduğu için görev otomatik kapanmamalı; görev manuel tamamlanmalıdır.

---

## 1.4 Aktivite sonucu / outcome mantığı

Aktivite sonuçları sabit enum olmayacak.

Sonuçlar:

- organizasyon bazlı olacak
- kullanıcı/admin tarafından yönetilebilir olacak
- eklenebilir, düzenlenebilir, pasife alınabilir olacak
- sadece etiket değil, davranış da taşıyacak

Örnek sonuçlar:

- ulaşıldı
- ulaşılamadı
- tekrar aranacak
- teklif istiyor
- çizim yapılacak
- çizim dosyası gönderilecek
- ilgisiz
- yanlış numara
- özel takip gerekiyor

Bu değerler sadece örnek/default seed olarak düşünülmelidir. Sistemde immutable enum olmamalıdır.

---

## 1.5 Sonuç davranışı satır durumunu belirler

Her organizasyon bazlı sonuç tanımı, worklist satırının **ana durumunu** belirleyecek şekilde yapılandırılmalıdır.

### Ana satır durumları

Her müşteri satırı bu görev kapsamında aşağıdaki ana durumlardan birinde olur:

| Ana durum | Açıklama |
|---|---|
| **Yapılmadı** | Bu görev kapsamında ilgili müşteri için henüz hiçbir işlem / aktivite yapılmadı. Sistem durumudur; outcome seçildiği anda satır bu durumdan çıkar. |
| **Takipte** | Bu görev kapsamında işlem yapıldı; konu henüz kapanmadı. |
| **Konu kapandı** | Bu görev kapsamında bu müşteri için artık yapılacak işlem kalmadı. |

**Yapılmadı** task/worklist context bazlıdır:

- Müşteri geçmişte başka bir görevde aranmış olabilir.
- Müşteri daha önce genel CRM aktivitesine sahip olabilir.
- Fakat **bu görev kapsamında** işlem yapılmadıysa satır **Yapılmadı** sayılır.

### Outcome → ana durum eşlemesi

Organizasyon bazlı outcome tanımları, satırın ana durumunu belirler. Outcome seçildiğinde ana durum yalnızca şunlardan biri olabilir:

- **Takipte**
- **Konu kapandı**

> Outcome seçildiyse satır artık **Yapılmadı** olamaz.

Örnek:

| Outcome | Ana durum |
|---|---|
| Ulaşıldı, görüşüldü | Konu kapandı |
| Ulaşılamadı | Takipte |
| Cuma tekrar ara | Takipte |
| Teklif istiyor | Takipte |
| Çizim yapılacak | Takipte |
| İlgilenmiyor | Konu kapandı |
| Yanlış numara | Takipte veya Konu kapandı (organizasyon kararı) |

### Ek davranış bayrakları (opsiyonel metadata)

Outcome tanımları ana duruma ek olarak aşağıdaki bayrakları taşıyabilir; bunlar ayrı ana filtre değildir:

- aksiyon gerekiyor
- veri problemi
- aktif/pasif
- sıralama

Örnek ek bayrak tablosu:

| Sonuç | Aksiyon gerekir | Veri problemi |
|---|---:|---:|
| Teklif istiyor | Evet | Hayır |
| Çizim yapılacak | Evet | Hayır |
| Yanlış numara | Evet | Evet |

---

## 1.6 Worklist ana filtreleri

Çalışma listesinde ana filtreler sade tutulacak.

Ana filtreler:

1. **Yapılmadı** *(varsayılan)*
2. **Takipte**
3. **Konu kapandı**
4. **Hepsi**

**Varsayılan açılış filtresi:** Yapılmadı

Ek olarak müşteri adına göre **arama** desteklenir; arama aktif filtreyi daraltır.

### Yapılmadı

Bu müşteri için **bu görev kapsamında** hiç işlem yapılmadı demektir. Task/worklist context bazlıdır; genel CRM geçmişi veya başka görevlerdeki işlemler bu filtreyi etkilemez.

### Takipte

Bu görev kapsamında işlem yapılmış; konu henüz kapanmamış demektir.

Örnekler:

- "Cuma günü tekrar ara"
- "Teklif istiyor"
- "Çizim yapılacak"
- "Yetkili dönüş yapacak"
- "Bilgi bekleniyor"

Bu durumda müşteri **Yapılmadı** filtresinde görünmez. Takip tarihi varsa `follow_up_at` alanında tutulur.

### Konu kapandı

Bu müşteri için **bu görev kapsamında** artık yapılacak işlem kalmadı demektir.

Örnekler:

- Görüşüldü, konu tamamlandı
- İlgilenmiyor
- Hedef dışı
- Bu görev için işlem gerekmiyor
- Arama sonucu kapandı

### Hepsi

Görev kapsamındaki tüm müşteri satırlarını gösterir: Yapılmadı, Takipte ve Konu kapandı birlikte listelenir.

### Kaldığın yerden devam etme

250 müşterilik listede kullanıcı bugün 80 müşteriyi işlediyse, bu 80 müşteri **Yapılmadı** filtresinden çıkar.

Yarın kullanıcı görevi açtığında varsayılan **Yapılmadı** filtresi ile sadece kalan müşteriler görünür.

Örnek:

- Toplam: 250
- Bugün işlenen: 80
- Yarın Yapılmadı filtresinde görünen: 170

Takipte olan müşteriler **Takipte** filtresinde ayrı görünür.

---

## 1.7 Liste tıklama davranışları

Çalışma listesinde iki ayrı kullanıcı aksiyonu olacak.

### Müşteri adına tıklama

Müşteri adına tıklanınca doğrudan müşteri kartına / müşteri detayına gidilecek.

Amaç:

- tam müşteri bilgisini incelemek
- kart detayında işlem yapmak
- geçmiş kayıtları detaylı görmek

### Aktivite butonuna tıklama

Satırdaki **Aktivite** butonuna basılınca listeden çıkmadan popup/modal açılacak.

Amaç:

- çok sayıda müşteri aranırken hızlı operasyon yapmak
- müşteri kartına gidip geri dönme zorunluluğunu kaldırmak
- arama sırasında gerekli müşteri bilgilerini modal içinde göstermek

---

## 1.8 Aktivite modal içeriği

Aktivite butonuna basıldığında açılan modalda aşağıdaki bilgiler gösterilecek:

- müşteri adı / firma özeti
- mevcut müşteri bilgileri
- telefonlar
- e-posta adresleri
- web sitesi
- adres / şehir / ülke
- contact / yetkililer
- önceki son aktiviteler
- görev bağlamı
- aktif organizasyon sonuç listesi
- yeni aktivite giriş alanı

Yeni aktivite girişinde en az şunlar olacak:

- sonuç seçimi
- not alanı
- opsiyonel contact/yetkili seçimi
- opsiyonel takip / tekrar arama tarihi (`follow_up_at`)
- **Kaydet** butonu
- **Kaydet ve sıradakine geç** butonu

### Modal kayıt butonları

#### Kaydet

Mevcut müşterinin aktivitesini kaydeder. Sonrasında:

- aktivite oluşturulur
- outcome davranışına göre worklist satırı güncellenir
- modal kapanabilir veya mevcut müşteri üzerinde kalabilir

#### Kaydet ve sıradakine geç

Mevcut müşterinin aktivitesini kaydeder. Sonrasında:

- aktivite oluşturulur
- outcome davranışına göre worklist satırı güncellenir
- mevcut aktif filtre ve sıralamaya göre sıradaki müşteri modalı açılır

Özellikle varsayılan **Yapılmadı** filtresinde kullanılacaktır.

Örnek akış:

1. Görev açılır; varsayılan filtre: Yapılmadı.
2. Kullanıcı ilk müşteride **Aktivite** butonuna basar.
3. Sonuç/not girer.
4. **Kaydet ve sıradakine geç** der.
5. Sistem sıradaki yapılmadı müşterinin modalını açar.
6. Kullanıcı listede kaybolmadan devam eder.

---

## 1.9 Aktivite detay popup'ı

Liste satırındaki son aktivite notu / özeti tıklanabilir olacak.

Satırda kısa özet gösterilecek.

Tıklanınca popup/modal içinde tam aktivite detayı gösterilecek:

- tam not
- sonuç
- tarih/saat
- aktiviteyi giren kullanıcı
- müşteri bilgisi
- bağlı görev bilgisi
- varsa contact/yetkili bilgisi

---

## 1.10 Görev tamamlama mantığı

Görev otomatik tamamlanmayacak.

Sebep:

> Liste dinamik olduğu için yeni müşteri sonradan listeye girebilir.

Kural:

- Sistem ilerleme durumunu hesaplar (Yapılmadı / Takipte / Konu kapandı sayıları).
- Kullanıcı görevi manuel tamamlar.
- "Tüm satırlar Konu kapandı" durumu sadece öneri/ilerleme göstergesi olabilir; otomatik görev kapatma kuralı olmamalıdır.

Varsayılan **Yapılmadı** filtresi sayesinde kullanıcı görevi tekrar açtığında kaldığı yerden devam edebilir (bkz. §1.6).

### Tamamlanmış görevde sonradan eklenen müşteriler

Görev `done` / tamamlandı durumundayken kaynak fuara yeni müşteri eklenirse:

- Görev **otomatik açılmaz**; `done` durumunda kalır.
- **Otomatik reopen yok.**
- **Otomatik yeni görev oluşturma yok.**

Görev detayında uyarı gösterilir:

> "Bu görev tamamlandıktan sonra X yeni müşteri eklendi."

Bu müşteriler çalışma listesinde normal akışı bozmayacak şekilde **ayrıca işaretlenir** (ör. satır badge / `added_after_completion` bayrağı). Dinamik liste mantığı devam eder; yeni satırlar listede görülebilir ancak görev durumu kullanıcı aksiyonu olmadan değişmez.

Kullanıcı seçenekleri:

- Görevi **manuel yeniden açarak** (status güncelleme) kalan işleri sürdürmek
- İlgili müşterileri **ayrıca işlemek** (müşteri kartı veya başka görev üzerinden)

---

## 1.11 `follow_up_at` alanı

`follow_up_at`, Faz 2'de yalnızca **bilgi / takip tarihi** alanı olarak tutulacak.

Faz 2'de:

- otomatik yeni görev üretmeyecek
- bildirim üretmeyecek
- takvim entegrasyonu yapmayacak

Kullanım amacı:

- takip tarihini listede göstermek
- Takipte filtrelerinde sıralama / hatırlatma mantığına temel olmak
- ileride Faz 3'te otomatik görev / hatırlatma üretimine altyapı hazırlamak

---

## 1.12 Satır bazlı kullanıcı atama

Faz 2'de satır bazlı kullanıcı atama **olmayacak**.

Kapsam dışı:

- müşteri satırını tek tek personele atama
- "bana atanan satırlar" filtresi
- ekip içi dağıtım algoritması

Görev sorumluluğu gerekirse görev seviyesindeki `assignee_user_id` alanı ile kalır.

---

# 2. Temel kullanıcı iş akışı

1. Kullanıcı yeni görev açar.
2. Görev örneği: "Foodist fuarına katılan tüm müşteriler aranacak."
3. Görevte kaynak olarak fuar/müşteri-fuar ilişkisi seçilir.
4. Sistem ilgili fuara bağlı müşterileri listeler.
5. Görev detayında çalışma listesi görünür; **varsayılan filtre: Yapılmadı**.
6. Kullanıcı müşteri adına tıklarsa müşteri kartına gider.
7. Kullanıcı Aktivite butonuna tıklarsa modal açılır.
8. Modalda müşteri özeti, iletişim bilgileri ve contact/yetkililer görünür.
9. Kullanıcı arama sonucunu seçer, not girer; isteğe bağlı `follow_up_at` girer.
10. **Kaydet** veya **Kaydet ve sıradakine geç** ile aktivite kaydedilir.
11. Seçilen outcome'a göre satır ana durumu güncellenir (Takipte veya Konu kapandı).
12. Liste ilerleme göstergeleri güncellenir.
13. Kullanıcı yarın görevi açtığında Yapılmadı filtresinde kalan müşterileri görür.
14. Görev kullanıcı tarafından manuel tamamlanır.
15. Görev tamamlandıktan sonra fuara yeni müşteri eklenirse görev `done` kalır; detayda uyarı gösterilir; satırlar işaretlenir; otomatik reopen olmaz.

---

# 3. Backend roadmap

## 3.1 Worklist state modeli

Liste dinamik olsa bile görev-müşteri bazlı state tutulmalıdır.

Tutulabilecek alanlar:

- organization_id
- task_id
- customer_id
- source_fair_id
- source relation bilgisi
- **primary_status** (`not_started` / `in_follow_up` / `closed`) — UI: Yapılmadı / Takipte / Konu kapandı
- last_activity_id
- last_outcome_id
- follow_up_at
- last_note_summary
- last_activity_at
- last_actor_user_id
- optional flags: action_required, data_problem
- **added_after_completion** (boolean) — müşteri, görev `completed_at` tarihinden sonra kaynak fuara eklenmişse `true`
- created_at
- updated_at

Not:

> Dinamik müşteri listesi ilişki tablosundan gelir; satır durumu ise task-customer state tablosundan okunur. State kaydı olmayan müşteri satırı **Yapılmadı** kabul edilir. `added_after_completion`, participation `created_at` ile görev `completed_at` karşılaştırmasıyla hesaplanır.

---

## 3.2 Outcome definition modeli

Organizasyon bazlı sonuç tanımı modeli kurulmalıdır.

Alan önerileri:

- organization_id
- name
- code / slug
- description
- is_active
- sort_order
- **primary_worklist_status** (`in_follow_up` | `closed`) — UI: Takipte | Konu kapandı
- requires_action (opsiyonel bayrak)
- marks_data_problem (opsiyonel bayrak)
- created_at
- updated_at

Default seed örnekleri olabilir; sistem bu değerlere bağlı hardcoded çalışmamalıdır.

---

## 3.3 Aktivite bağlantısı

Modaldan aktivite kaydedildiğinde aşağıdaki bağlantılar kurulmalıdır:

- activity → organization
- activity → customer
- activity → task
- activity → worklist item/state
- activity → outcome definition
- activity → optional contact
- activity → optional follow_up_at

Kaydetme sonrası:

- aktivite oluşturulur
- task-customer state güncellenir (primary_status + follow_up_at + özet alanlar)
- outcome davranışı uygulanır
- güncel satır verisi frontend'e döner

---

## 3.4 Worklist API

Görev detayından çalışma listesi çekilebilmelidir.

Ana filtreler:

- **yapilmadi** *(varsayılan)*
- **takipte**
- **konu_kapandi**
- **hepsi**

Ek:

- müşteri adına göre arama

Dönen bilgiler:

- customer_id
- customer_name
- city / country
- phone summary
- email summary
- contact count
- last outcome
- last activity note summary
- last activity date
- primary_status
- follow_up_at (varsa)
- optional flags (action_required, data_problem)
- added_after_completion (boolean)

Görev detay response'unda ek alan:

- **post_completion_new_customer_count** — tamamlanma tarihinden sonra eklenen müşteri sayısı (uyarı metni için)

---

## 3.5 Aktivite modal data API

Aktivite butonuna basıldığında modal için veri dönecek endpoint gerekir.

Dönmesi gerekenler:

- müşteri temel bilgileri
- iletişim bilgileri
- telefonlar
- e-postalar
- web sitesi
- adres / şehir
- contact/yetkililer
- önceki son aktiviteler
- görev bağlamı
- organizasyonun aktif sonuç listesi

---

## 3.6 Aktivite kaydetme API

Modal üzerinden aktivite kaydetme endpoint'i gerekir.

Girdi:

- task_id
- customer_id
- activity_type
- outcome_id
- note
- optional contact_id
- optional follow_up_at
- **advance_to_next** (boolean) — `true` ise Kaydet ve sıradakine geç davranışı

Çıktı:

- oluşturulan aktivite bilgisi
- güncel worklist row state
- güncel progress istatistikleri
- `advance_to_next=true` ise sıradaki müşteri için modal context (varsa)

---

## 3.7 Aktivite detay API

Son aktivite notuna tıklanınca tam detay için endpoint gerekir.

Dönmesi gerekenler:

- tam not
- sonuç
- tarih/saat
- kullanıcı
- müşteri
- görev
- varsa contact/yetkili
- varsa follow_up_at

---

# 4. Frontend roadmap

## 4.1 Görev detayında çalışma listesi

Görev detay ekranına "Çalışma Listesi" bölümü eklenmelidir.

Tamamlanmış görevde `post_completion_new_customer_count > 0` ise üstte uyarı bandı gösterilir:

> "Bu görev tamamlandıktan sonra X yeni müşteri eklendi."

Sonradan eklenen müşteri satırları listede ayrıca işaretlenir; görev durumu otomatik değişmez.

Tablo alanları:

- müşteri adı
- telefon
- e-posta
- şehir
- yetkili/contact sayısı
- son sonuç
- son not özeti
- durum (Yapılmadı / Takipte / Konu kapandı)
- takip tarihi (`follow_up_at`, varsa)
- sonradan eklendi işareti (`added_after_completion`, varsa)
- Aktivite butonu

---

## 4.2 Tıklama davranışları

- Müşteri adına tıklayınca müşteri kartına gidilir.
- Aktivite butonuna tıklayınca modal açılır.
- Son aktivite notu/özeti tıklanınca aktivite detay popup'ı açılır.

---

## 4.3 Aktivite modalı

Modal bölümleri:

1. Müşteri özeti
2. İletişim bilgileri
3. Contact/yetkililer
4. Son aktiviteler
5. Yeni aktivite girişi

Yeni aktivite alanları:

- sonuç seçimi
- not alanı
- contact seçimi
- takip / tekrar arama tarihi (`follow_up_at`) — yalnızca bilgi alanı
- **Kaydet**
- **Kaydet ve sıradakine geç**

---

## 4.4 Filtreler

Çalışma listesinde ana filtreler:

| Filtre | Varsayılan |
|---|---|
| Yapılmadı | ✓ (açılış filtresi) |
| Takipte | |
| Konu kapandı | |
| Hepsi | |

Ek: müşteri adına göre arama.

Faz 2'de ayrı ana filtre olmayanlar: işlem yapıldı, aksiyon gerekiyor, veri problemi, sonuç tipi (bunlar outcome metadata veya ileride genişletme olarak değerlendirilebilir).

---

## 4.5 İlerleme göstergesi

Görev üzerinde özet görünmeli:

- toplam müşteri
- yapılmadı
- takipte
- konu kapandı

Örnek:

> 248 müşteri / 170 yapılmadı / 25 takipte / 53 konu kapandı

---

## 4.6 Sonuç yönetim ekranı

Organizasyon bazlı sonuçlar için basit yönetim ekranı gerekir.

Önerilen yer:

> Ayarlar / Görev Sonuçları  
> veya  
> CRM Aktivite Sonuçları

İşlemler:

- sonuç ekle
- sonuç düzenle
- pasife al
- sıralama değiştir
- **ana durum seç** (Takipte / Konu kapandı)
- opsiyonel ek bayrakları seç (aksiyon gerekiyor, veri problemi)

---

# 5. Teslim sırası

## Sprint 1 — Backend temel yapı

- Worklist state modeli (`primary_status`, `follow_up_at`)
- Görev → müşteri listesi dinamik sorgu mantığı
- Task-customer state kayıt yapısı
- Outcome definition modeli (`primary_worklist_status`)
- Migration ve temel testler

### Sprint 1 uygulama notları (onaylı)

#### `source_fair_id` değişimi

- Worklist state kaydı oluşmuşsa `source_fair_id` **değiştirilemez**.
- Görev `done` / tamamlandı durumundaysa `source_fair_id` **değiştirilemez**.
- Bu kurallar Sprint 3 use case katmanında enforce edilir; domain helper ile test edilir.

#### Worklist status

- DB: `crm_todo_worklist_states.primary_status` yalnızca `in_follow_up` | `closed` tutar.
- `not_started` DB'de **tutulmaz**; state satırı yoksa virtual/computed status olarak kabul edilir.
- API/response (Sprint 3+): worklist satırında `not_started` computed status olarak döner.

#### Outcome delete

- Outcome tanımı **fiziksel silinmez**.
- Kullanılmış veya kullanılmamış olsa bile delete yerine `is_active = false` ile pasife alınır.
- Eski activity/worklist kayıtları `last_outcome_id` referansını korur.

#### Sprint 1 kapsam sınırı

- Public API ve frontend değişikliği **yok**.
- Alembic merge + foundation migration + domain + repository + roundtrip testler.

## Sprint 2 — Outcome yönetimi

- Organizasyon bazlı outcome CRUD
- Default outcome seed'leri
- Aktif/pasif desteği
- Ana durum eşlemesi + opsiyonel bayraklar
- Yetki ve organizasyon izolasyonu

## Sprint 3 — Worklist API

- Görev çalışma listesi endpoint'i
- Ana filtreler (Yapılmadı / Takipte / Konu kapandı / Hepsi); varsayılan Yapılmadı
- Satır state hesapları
- Progress/istatistik endpoint'i
- Testler

## Sprint 4 — Aktivite modal API

- Modal müşteri özet endpoint'i
- Contact/yetkili bilgileri
- Son aktiviteler
- Aktivite kaydetme (`advance_to_next` desteği)
- Outcome davranışına göre state güncelleme
- Testler

## Sprint 5 — Frontend liste

- Görev detayında çalışma listesi tablosu
- Ana filtreler; varsayılan Yapılmadı
- Tamamlanmış görevde sonradan eklenen müşteri uyarı bandı + satır işareti
- Müşteri adına tıklama
- Aktivite butonu
- İlerleme göstergesi

## Sprint 6 — Modal ve popup

- Aktivite modalı (Kaydet + Kaydet ve sıradakine geç)
- Müşteri özeti
- İletişim bilgileri
- Contact/yetkililer
- Yeni aktivite kaydı + follow_up_at alanı
- Son aktivite detay popup'ı

## Sprint 7 — Test ve dokümantasyon

- Backend testleri
- Frontend davranış testleri
- Organizasyon izolasyonu testleri
- Dinamik liste davranışı
- Varsayılan Yapılmadı filtresi ve sıradakine geç akışı
- Yetki kontrolleri
- Faz 2 dokümantasyonu

---

# 6. Kabul kriterleri

Faz 2 aşağıdakiler sağlandığında tamam kabul edilir:

1. Görevten müşteri bazlı çalışma listesi açılabiliyor.
2. Liste müşteri-fuar ilişkisinden geliyor.
3. Liste dinamik çalışıyor.
4. Foodist'e yeni müşteri eklenirse listeye otomatik giriyor.
5. Müşteri adına tıklanınca müşteri kartına gidiyor.
6. Aktivite butonuna basınca listeden çıkmadan modal açılıyor.
7. Modalda müşteri özeti, iletişim bilgileri ve contact/yetkililer görünüyor.
8. Modal üzerinden aktivite girilebiliyor.
9. Aktivite sonucu organizasyon bazlı tanımlardan seçiliyor.
10. Sonuç davranışı satır ana durumunu (Takipte / Konu kapandı) otomatik güncelliyor.
11. Son aktivite notu listede kısa özet olarak görünüyor.
12. Nota tıklanınca tam aktivite detayı popup'ta açılıyor.
13. Ana filtreler (Yapılmadı / Takipte / Konu kapandı / Hepsi) çalışıyor; varsayılan filtre Yapılmadı.
14. Yapılmadı tanımı task/worklist context bazlı uygulanıyor.
15. Görev ilerlemesi (toplam / yapılmadı / takipte / konu kapandı) görülebiliyor.
16. Modalda Kaydet ve Kaydet ve sıradakine geç butonları çalışıyor.
17. `follow_up_at` yalnızca bilgi alanı olarak tutuluyor; otomasyon üretmiyor.
18. Görev manuel tamamlanabiliyor.
19. Organizasyon izolasyonu korunuyor.
20. Yetki kontrolleri mevcut Todo/Fair CRM permission yapısına uyuyor.
21. Tamamlanmış görevde sonradan eklenen müşteriler için uyarı gösteriliyor; görev otomatik açılmıyor.
22. Sonradan eklenen müşteriler listede ayrıca işaretleniyor; otomatik reopen veya otomatik yeni görev yok.

---

# 7. Faz 2 kapsam dışı

Şimdilik kapsam dışı bırakılacaklar:

- kişi bazlı çalışma listesi
- lead bazlı çalışma listesi
- katılımcı kişi bazlı çalışma listesi
- **satır bazlı kullanıcı atama** ("bana atanan satırlar", ekip dağıtımı)
- otomatik yeni görev oluşturma
- **tamamlanmış görevin otomatik yeniden açılması (auto-reopen)**
- gelişmiş dağıtım/atama algoritması
- **`follow_up_at` üzerinden otomatik görev, bildirim veya takvim üretimi**
- toplu SMS/e-posta
- otomatik arama entegrasyonu
- Excel export
- AI not özeti
- kampanya otomasyonu

Bunlar Faz 3 veya sonrası için değerlendirilebilir.

---

# 8. Karar özeti

Faz 2 uygulamasına başlamadan önce netleştirilmesi gereken tüm kararlar kapanmıştır.

| Konu | Karar |
|---|---|
| Ana filtre yapısı | Yapılmadı / Takipte / Konu kapandı / Hepsi; varsayılan **Yapılmadı** |
| Yapılmadı tanımı | Bu görev kapsamında hiç işlem yapılmadı; task-context bazlı |
| `follow_up_at` | Faz 2'de yalnızca bilgi/takip tarihi alanı; otomasyon yok |
| Satır bazlı kullanıcı atama | Faz 2 kapsam dışı; görev seviyesinde assignee yeterli |
| Modal kayıt sonrası akış | **Kaydet** ve **Kaydet ve sıradakine geç** butonları dahil |
| Tamamlanmış görevde yeni müşteri | Görev `done` kalır; otomatik reopen/yeni görev yok; detayda **"Bu görev tamamlandıktan sonra X yeni müşteri eklendi."** uyarısı; satırlar `added_after_completion` ile işaretlenir; kullanıcı manuel yeniden açar veya müşterileri ayrı işler |

---

# 9. Geliştiriciye başlangıç talimatı

Bu Faz 2'ye başlanırken önce mevcut Faz 1 Todo modülü incelenmelidir.

İlk bakılacak alanlar:

- Todo/task backend CRUD yapısı
- Todo role/permission matrix
- Todo frontend sayfası ve navigation
- Customer model ve customer detail ekranı
- Fair participation / customer-fair ilişki modeli
- Activity model/service varsa mevcut aktivite kayıt yapısı
- Organization isolation pattern
- Alembic migration pattern
- Frontend modal/table component pattern

Uygulamaya başlamadan önce bu dokümandaki kararlarla çelişen mevcut yapı varsa not alınmalı ve önce kısa teknik öneri çıkarılmalıdır.

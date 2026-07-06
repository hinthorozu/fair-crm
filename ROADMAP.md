# FAIR CRM Roadmap

Bu doküman FAIR CRM için yapılan işleri ve bundan sonra yapılacak işleri iki ana başlık altında toplar.

---

## 1. Yapılmış İşler

### Altyapı / Core

- Core permission seed sistemi kuruldu.
- FAIR CRM permission set genişletildi.
- Dev identity / owner role permission assignment tamamlandı.
- Auth servis erişilemezken 500 yerine kontrollü 403 dönüşü sağlandı.
- Alembic migration zinciri toparlandı.
- Dev reset / seed akışı çalışır hale getirildi.

### Müşteri / CRM Temeli

- Müşteri listeleme yapısı kuruldu.
- Müşteri detay/kart ekranı oluşturuldu.
- Telefon, email, şehir, ülke gibi özet bilgiler gösteriliyor.
- Duplicate customer analysis iyileştirildi.
- Yanlış fuzzy merge sorunları azaltıldı.
- Firma adı eşleştirme kuralları güçlendirildi.

### Import / Veri Alma

- Import altyapısı kuruldu.
- Fuar katılımcılarından müşteri oluşturma akışı çalışır hale geldi.
- Import geçmişi / durum takibi temel seviyede var.
- Import edilen müşteri verileri görev/worklist kaynağı olarak kullanılabilir hale geldi.

### SMTP / Mail Altyapısı

- Ortak SMTP mailer katmanı oluşturuldu.
- SMTP connect timeout / send timeout / operation timeout eklendi.
- Timeout hataları normalize edildi.
- Fair bulk worker’da tek mail hatası batch’i komple düşürmeyecek hale getirildi.
- Mail event zinciri yazılıyor.

### Dashboard

- Dashboard summary 500 hatası çözüldü.
- camelCase / snake_case Pydantic uyumsuzluğu düzeltildi.
- Sayaçlar null-safe hale getirildi.
- Recent activities fallback eklendi.
- Dashboard summary endpoint 200 döner hale geldi.

### Sprint 4 — Görevler Worklist

- Sidebar’a Görevler eklendi.
- Görev listesi ve detay ekranı yapıldı.
- Görev oluşturma + kaynak fuar seçimi eklendi.
- Worklist, fuar katılımcılarından doluyor.
- Filtreler çalışıyor: Yapılmadı, Takipte, Konu kapandı, Hepsi.
- Progress kartları çalışıyor: Toplam, Yapılmadı, Takipte, Konu kapandı.
- Müşteri adına tıklayınca Müşteri işlemi modalı açılıyor.
- Modalda outcome, not, takip tarihi, action_required ve data_problem kaydediliyor.
- Kaydet ve sıradakine geç çalışıyor.
- Liste ve progress yenileniyor.
- Sağ aksiyon Müşteri Kartı oldu.
- source_fair_id olmayan görevlerde kullanıcı dostu uyarı gösteriliyor.
- Çift pagination düzeltildi.
- Responsive temel kabul yapıldı.
- Sprint 4 kabul edildi.
- Referans commit: 9d17010 - fix: repair todo worklist activity modal actions.

### Sprint 5 — Takipler

- Sidebar’a Takipler eklendi.
- /follow-ups ekranı yapıldı.
- Worklist state kayıtları tek takip ekranında toplanıyor.
- Filtreler çalışıyor: Bugün, Geçmiş, Aksiyon gerekenler, Veri problemi, Hepsi.
- Müşteri adına tıklayınca işlem modalı açılıyor.
- Müşteri adına tıklayınca müşteri kartına gidilmiyor.
- Sağdaki Müşteri Kartı butonu müşteri detayına gidiyor.
- Sprint 4 modalı reuse edildi.
- Kayıt sonrası takip listesi yenileniyor.
- Kaydet ve sıradakine geç, takip listesindeki sıradaki müşteriye geçiyor.
- Manuel UI demo 13/13 geçti.

---

## 2. Yapılacak İşler

### Sprint 5 Kapanış

- Sprint 5 commit + push yapılacak.
- Build/test özeti alınacak.
- Sprint 5 resmi kapatılacak.
- Commit mesajı: feat: add follow-ups screen with worklist activity modal reuse (Sprint 5).

### Responsive Polish

- 390px imports toolbar taşması temizlenecek.
- 390px scraper run-history toolbar taşması temizlenecek.
- 390px worklist/customers 10–12px hafif taşma temizlenecek.
- Mobil toolbar CSS standardı iyileştirilecek.
- Mobil/tablet kullanımında tablo, toolbar, pagination ve modal davranışı daha da güçlendirilecek.

### Task Engine / Operation Tasks

Görevler sadece fuara bağlı kalmayacak. Uzun vadede görevler operasyon motoruna dönüşecek.

Hedef görev tipleri:

- call_followup
- bulk_email
- enrichment
- data_cleanup
- reminder

Hedef kaynak tipleri:

- fair
- multiple_fairs
- import
- segment
- manual_selection

Amaç:

- X fuarındaki müşterileri ara.
- X, Y, Z fuarlarındaki müşterilere otomatik mail gönder.
- 1, 2, 3 fuarındaki müşterilerin zenginleştirme çalışmasını yap.
- Eksik verili müşterileri temizle.
- Takip tarihi gelenleri otomatik takip listesine düşür.
- Veri problemi olanları ayrı operasyon listesine al.
- Mail sonrası dönüş bekleyenlere hatırlatma oluştur.

### Multi-source Görev Kaynağı

Mevcut yapı:

- source_fair_id

Gelecek yapı:

- source_type
- source_ids

Desteklenecek kaynaklar:

- Tek fuar
- Çoklu fuar
- Import
- Segment
- Manuel müşteri seçimi
- Etiketli müşteri grubu

Amaç:

- Görevler sadece tek fuara bağlı kalmayacak.
- Kullanıcı birden fazla fuardan görev oluşturabilecek.
- Import edilen müşteri listeleri görev kaynağı olabilecek.
- Filtrelenmiş müşteri segmentleri görev kaynağı olabilecek.
- Manuel seçilmiş müşteri listeleri görev kaynağı olabilecek.

### Otomatik Mail Görevleri

Amaç:

- Kullanıcı X, Y, Z fuarlarındaki müşterilere seçilen mail şablonunu gönderebilecek.

Kapsam:

- Görev tipi bulk_email.
- Tek fuar seçimi.
- Çoklu fuar seçimi.
- Segment seçimi.
- Mail template seçimi.
- SMTP hesabı seçimi.
- Gönderim kuyruğu.
- Başarılı gönderim takibi.
- Failed gönderim takibi.
- Timeout takibi.
- Bounced mail takibi.
- Mail sonrası otomatik takip görevi oluşturma.
- Mail aktivitelerini müşteri geçmişine yazma.
- Mail gönderim durumunu dashboard’da gösterme.

### Zenginleştirme Görevleri

Amaç:

- Kullanıcı 1, 2, 3 fuarındaki müşterilerin zenginleştirme çalışmalarını başlatabilecek.

Kapsam:

- Eksik telefon kontrolü.
- Eksik email kontrolü.
- Eksik website kontrolü.
- Eksik şehir / ülke kontrolü.
- Hatalı kategori kontrolü.
- Firma adı normalize.
- Data problem flag üretme.
- Zenginleştirme state takibi.
- Zenginleştirme sonucu müşteri kartına işleme.
- Zenginleştirme sonucu aktivite geçmişine yazma.

### Veri Temizleme Görevleri

- Duplicate müşteri kontrolü.
- Eksik email listesi.
- Eksik telefon listesi.
- Hatalı ülke / şehir listesi.
- Hatalı firma adı listesi.
- Data problem işaretli müşteriler.
- Normalize edilmesi gereken alanlar.
- Temizlik sonrası müşteri kartı güncellemesi.
- Temizlik aktivitelerinin kayıt altına alınması.

### Hatırlatma / Takip Motoru

- Bugünkü takipler.
- Geciken takipler.
- Action required olan işler.
- Mail sonrası geri dönüş beklenenler.
- Yeniden aranacak müşteriler.
- Kullanıcı bazlı takip listeleri.
- Takip tarihi değişince liste güncelleme.
- Takip tamamlanınca ilgili listeden düşürme.

### Müşteri Timeline / Aktivite Geçmişi

- Müşteri kartında timeline.
- Worklist aktiviteleri timeline’da görünecek.
- Takip aktiviteleri timeline’da görünecek.
- Mail aktiviteleri timeline’da görünecek.
- Arama/takip notları görünecek.
- Outcome geçmişi görünecek.
- Kullanıcı kimin ne zaman işlem yaptığını görebilecek.
- Takip tarihi değişiklikleri görülebilecek.
- Action required / data problem değişiklikleri görülebilecek.

### Dashboard / Operasyon Özeti

- Bugünkü takipler.
- Geciken takipler.
- Aksiyon gerekenler.
- Veri problemi olanlar.
- Açık görevler.
- Kapanan konular.
- Mail gönderim durumu.
- Son aktiviteler.
- Toplam açık takip.
- Bugün kapanan işler.
- Görev bazlı ilerleme.
- Fuar bazlı durum.
- Kullanıcı bazlı işlem sayıları.
- Mail başarısızlıkları.
- Timeout sayıları.

### UI / UX Kalite

- Modal ve form standartları tüm ekrana yayılacak.
- DataTable standardı tüm listelerde aynı olacak.
- Empty state standardı yapılacak.
- Loading state standardı yapılacak.
- Error state standardı yapılacak.
- Türkçe label tutarlılığı sağlanacak.
- Ana aksiyon / yan aksiyon ayrımı tüm ekranlarda uygulanacak.
- Mobil/tablet responsive polish devam edecek.
- Toolbar / pagination standardı netleştirilecek.
- Sayfa header / breadcrumb davranışı standart hale getirilecek.
- Form grid davranışı tüm ekranlarda tutarlı olacak.
- Buton metinleri açık ve kullanıcı dostu olacak.

### Raporlama

- Görev bazlı performans.
- Fuar bazlı müşteri durumu.
- Mail gönderim raporu.
- Outcome dağılımı.
- Takip dönüşüm oranı.
- Veri kalitesi raporu.
- Kullanıcı bazlı işlem raporu.
- Geciken takip raporu.
- Kapanan konu raporu.
- Data problem raporu.

### İleri Aşama

- Segment builder.
- Etiket sistemi.
- Otomasyon kuralları.
- Hatırlatma motoru.
- Mail kampanya akışı.
- WhatsApp entegrasyonu.
- Yetki bazlı UI görünürlüğü.
- Audit log ekranı.
- Gelişmiş müşteri segmentasyonu.
- Otomatik müşteri puanlama.
- Operasyon bazlı bildirimler.
- Kullanıcıya özel iş listeleri.

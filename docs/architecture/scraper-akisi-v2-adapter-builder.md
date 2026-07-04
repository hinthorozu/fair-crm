# Scraper Akışı v2 — Adapter Builder Vizyonu

**Modül:** Data Integration / Scraper  
**Durum:** Vizyon referans dokümanı (henüz uygulanmadı)  
**İlgili:** [SOURCE_ADAPTER_FRAMEWORK.md](../import/SOURCE_ADAPTER_FRAMEWORK.md), [IMPORT_ARCHITECTURE.md](../import/IMPORT_ARCHITECTURE.md), [PRODUCT_VISION.md](../PRODUCT_VISION.md)

---

## Amaç

FAIR CRM scraper sistemi artık yalnızca manuel adapter yazılan bir yapı olmayacak.

**Yeni hedef:**

Kullanıcı fuar URL’si girer; sistem mümkün olduğunca kendi adapter’ını üretir. AI yalnızca sistem başaramadığında manuel destek için devreye girer.

Bu doküman gelecek geliştirmeler için referanstır. **Mevcut aktif işi bozmaz.** Adapter Yönetimi, Adapter CRUD ve Fuar entegrasyonu korunacak; v2 Adapter Builder bunların üzerine inşa edilecektir.

---

## Nihai Akış

```text
Fuar URL gir
    ↓
Adapter Builder — siteyi analiz et
    ↓
Liste yapısını bul
    ↓
Pagination bul
    ↓
Detail linklerini bul
    ↓
Alan tespiti (firma adı, telefon, mail, website, stand, salon)
    ↓
Manifest taslağı üret
    ↓
Test scrape yap
    ↓
Confidence score hesapla
    ↓
Karar (otomatik / onay / manuel)
```

| Adım | Çıktı |
|------|--------|
| Site analizi | DOM yapısı, sayfa türleri (liste / detay), teknoloji ipuçları |
| Liste yapısı | Katılımcı satırı / kart selector’ları |
| Pagination | Sayfa numarası, “sonraki”, sonsuz scroll vb. |
| Detail linkleri | Liste → detay URL kalıbı |
| Alan tespiti | Canonical alanlara eşleşen selector veya extract kuralları |
| Manifest taslağı | Kayıtlı adapter formatına uygun JSON manifest |
| Test scrape | Örnek N kayıt (liste + isteğe bağlı detay) |
| Confidence score | Tüm adımların birleşik güven skoru |

---

## Karar Mantığı

Confidence score, site analizi + selector güveni + test scrape sonuçlarından türetilir.

| Güven aralığı | Davranış |
|---------------|----------|
| **%95 ve üzeri** | Adapter otomatik oluşturulabilir |
| **%80 – %95** | Önizleme göster; kullanıcı onayı iste |
| **%80 altı** | Manuel müdahale gerekli |

Onay gerektiren senaryolarda kullanıcı manifest taslağını, örnek kayıtları ve düşük güvenli alanları görür; onaylamadan adapter kaydedilmez.

---

## Kritik Kural — CRM’e Doğrudan Yazım Yok

Scraper / Adapter çalışması tamamlandığında sonuçlar CRM’e **doğrudan yazılmaz**.

Sistem scraper çıktısını, kullanıcının **Excel import etmiş gibi** ele alır. Scraper sonucu Universal Import Engine hattına düşer:

```text
Scraper sonucu
    ↓
Import Batch
    ↓
Import Preview
    ↓
Duplicate Detection
    ↓
Merge Decision
    ↓
CRM
```

Önceki özet akış (`Adapter → Import Preview → …`) aynı prensibi ifade eder; Run v2 ve sonrasında ara katman **Import Batch** olarak netleşir.

Bu kural [SOURCE_ADAPTER_FRAMEWORK.md](../import/SOURCE_ADAPTER_FRAMEWORK.md) ile uyumludur: adapter kaynak okur ve normalize eder; eşleştirme, birleştirme ve kalıcı yazım Import Engine sorumluluğundadır.

Adapter Builder yalnızca **adapter + manifest** üretir. Üretilen veri Import Wizard / Preview hattına beslenir; operatör onayı olmadan CRM’e kayıt oluşmaz.

---

## Dip Not — Import Mantığı

**Fuar → Adapter seçimi** yalnızca **kaynak bağlantısını** hazırlar: hangi adapter, hangi `source_url`, isteğe bağlı `scraper_config`. Bu alanlar fuar kaydına yazılır; CRM müşteri/katılım tablolarına veri yazmaz.

Run v2 geldiğinde scraper çıktısı, Excel import ile **aynı** import / preview / merge mantığını kullanacaktır:

| Aşama | Excel import | Scraper / Run v2 (hedef) |
|-------|--------------|---------------------------|
| Ham veri | Dosya yükleme | Adapter scrape sonucu |
| Batch | Import job / batch | Import Batch |
| Önizleme | Import Preview | Import Preview |
| Eşleşme | Duplicate Detection | Duplicate Detection |
| Karar | Merge Decision | Merge Decision |
| Kalıcı yazım | CRM (onay sonrası) | CRM (onay sonrası) |

Bu nedenle scraper’a özel “doğrudan CRM yaz” veya ayrı merge motoru **planlanmaz**. Tek Import Engine, tek preview/merge deneyimi.

---

## AI Kullanımı

AI ana mekanizma **değildir**.

Deterministik analiz (DOM traversal, kalıp eşleştirme, bilinen fuar site şablonları, test scrape doğrulaması) birincil yöntemdir. AI yalnızca aşağıdaki durumlarda devreye girer:

| Durum | AI rolü |
|-------|---------|
| Sistem siteyi analiz edemezse | Yapı yorumlama, alternatif selector önerisi |
| Selector güveni düşükse | Alan eşleştirme ve selector iyileştirme önerisi |
| JavaScript / anti-bot / karmaşık yapı | Dinamik içerik stratejisi, manuel adapter iskeleti |
| Manuel adapter desteği gerekirse | Geliştirici / operatör için açıklama ve patch önerisi |

AI çıktıları her zaman test scrape ve confidence score ile doğrulanır; otomatik CRM yazımı veya otomatik adapter aktivasyonu AI kararıyla yapılmaz.

---

## Mevcut Sistemle İlişki

v2 vizyonu, halihazırda çalışan bileşenleri **değiştirmek yerine genişletir**:

| Mevcut (korunacak) | v2 ile ilişki |
|--------------------|---------------|
| Adapter Yönetimi UI | Üretilen adapter’ların listelenmesi, düzenlenmesi, aktif/pasif |
| Adapter CRUD API | Builder çıktısının `scraper_adapters` kaydına dönüşümü |
| Fuar ↔ adapter ilişkisi | Kaynak bağlantısı (`adapter_key`, `source_url`, `scraper_config`); scrape sonucu değil |
| Scraper run / test console | Test scrape ve confidence doğrulaması için mevcut altyapı |

Adapter Builder ayrı bir geliştirme hattı olarak planlanmalı; Sprint kapsamı ve API sözleşmeleri bu dokümandan türetilecek ayrı teknik tasarımlarda netleştirilecektir.

---

## Özet

1. Kullanıcı URL girer; sistem adapter’ı mümkün olduğunca kendisi üretir.  
2. Güven skoruna göre otomatik, onaylı veya manuel yol seçilir.  
3. Scraper sonucu → Import Batch → Import Preview → Duplicate Detection → Merge Decision → CRM zinciri değişmez; Excel ile aynı Import Engine.  
4. AI yedek ve destek mekanizmasıdır; birincil yol deterministik Adapter Builder’dır.  
5. Mevcut Adapter CRUD, Fuar entegrasyonu ve Fuar → Adapter seçimi korunur; seçim yalnızca kaynak bağlantısını hazırlar.

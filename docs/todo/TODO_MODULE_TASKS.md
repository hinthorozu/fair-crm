# FAIR CRM To-Do Module — Yapılacak İşler

## Amaç

Bu dosya To-Do modülünün teknik yapılacak işlerini takip etmek için oluşturulmuştur.

Bu fazda sadece bağımsız, organizasyon bazlı To-Do modülü yapılacaktır.

---

## Implementasyon Sırası / Implementation Plan

Onaylanmış Faz 1 uygulama sırası. Referans modüller: `customers` (liste/filtre/archive), `activities` (entity + CRUD), `smtp` (permission + use case).

### Genel sıra

```text
1. Backend (domain → migration → repo → use case → API → permission wiring)
2. Frontend (types/API → liste → form/detay → aksiyonlar → nav)
3. Test (backend birim/API eşzamanlı; role matrix + frontend build en sonda)
```

Backend tamamlanmadan frontend'e geçilmemeli. API sözleşmesi (response alanları, filtre parametreleri, permission kodları) netleşmeden UI yazılmamalı.

### Backend sırası

| Adım | İş | Bağımlılık |
|------|-----|------------|
| **B1** | Domain: `Todo` entity, `TodoStatus` / `TodoPriority` / `TodoCategory` enum'ları, domain exceptions, repository port | — |
| **B2** | Alembic migration: `crm_todos` tablosu (`organization_id` index, enum string kolonlar, `archived_at` / `completed_at`, audit alanları) | B1 |
| **B3** | Infrastructure: SQLAlchemy model + mapper + `SqlAlchemyTodoRepository` (org-scoped sorgular) | B2 |
| **B4** | Application: commands/DTO/mappers + use case'ler (`Create`, `Get`, `List`, `Update`, `Complete`, `Archive`, `Delete`) | B3 |
| **B5** | Liste mantığı: filtreler, sayfalama/sıralama | B4 |
| **B6** | Overdue: response'a `is_overdue` — `deadline < now AND status != done` | B5 |
| **B7** | API: `schemas`, `dependencies`, `routes`; router kaydı (`/api/v1/todos`) | B4–B6 |
| **B8** | Permission: use case'lerde `fair_crm.todos.*` kontrolleri + `scripts/fair_crm_role_matrix.py` güncellemesi | B7 |

**B4 iç öncelik:** Create + Get → List + filtreler → Update → Complete / Archive → Delete (yalnızca `fair_crm.todos.delete`).

**Delete vs archive:** UI “sil” davranışı archive endpoint/permission ile; gerçek silme `DELETE /todos/{id}` + `fair_crm.todos.delete` (owner/admin).

### Frontend sırası

| Adım | İş | Bağımlılık |
|------|-----|------------|
| **F1** | `types/todo.ts`, `api/todos.ts`, `labels/todoLabels.ts` (TR etiketler, enum map'leri) | B7 |
| **F2** | `permissions/todoPermissions.ts` (+ unit test) | F1 |
| **F3** | Ana liste: `TodosPage` — `ServerDataTableFrame`, URL sync, 9 kolon, overdue badge | F1 |
| **F4** | Liste filtreleri (8 filtre + arama) | F3 |
| **F5** | Create/Edit form modal | F1 |
| **F6** | Detay ekranı (`/todos/{id}`) veya genişletilmiş modal | F5 |
| **F7** | Satır aksiyonları: Tamamla, Arşivle; delete yalnızca permission varsa | F2, F3 |
| **F8** | Navigasyon: `App.tsx` route, sidebar menü | F3 |

**F3 assignee/creator gösterimi:** Faz 1'de Core org-members entegrasyonu yok; mevcut kullanıcı/üyelik datası varsa isim, yoksa UUID/boş gösterim kabul (bkz. `TODO_MODULE_DECISIONS.md` §12).

### Test sırası

| Aşama | Ne zaman | Kapsam |
|-------|----------|--------|
| **T1** | B1 sonrası | Domain/entity: enum validation, complete/archive geçişleri, overdue mantığı |
| **T2** | B3 sonrası | Repository: org izolasyonu, filtreler, `include_archived`, search |
| **T3** | B7 sonrası | API integration: CRUD, complete, archive, 403/404 |
| **T4** | B8 sonrası | Permission: yetkisiz delete, archive yetkisi, org dışı erişim |
| **T5** | B8 sonrası | `test_role_matrix_authorization.py`: todos permission satırları |
| **T6** | F7 sonrası | `npm run build`; permission unit testleri |
| **T7** | Kapanış | Tam pytest suite + manuel smoke |

**Test öncelik:** org izolasyonu → CRUD + enum → complete/archive → overdue → delete yetkisi → filtreler/search → role matrix.

### Önerilen teslim dilimleri (PR)

1. **PR-1:** Backend domain + migration + repo + temel CRUD API + T1–T3
2. **PR-2:** Complete / archive / delete + filtreler + overdue + permissions + T4–T5
3. **PR-3:** Frontend liste + formlar + aksiyonlar + nav + T6–T7

### Riskler (özet)

| Risk | Azaltma |
|------|---------|
| Core RBAC: yeni permission kodları | `fair_crm_role_matrix.py` + Core permission tanımı (ayrı ticket) |
| Category encoding | DB/API ASCII slug; TR yalnızca UI label (bkz. karar §11) |
| Assignee/creator isimleri | Faz 1'de UUID/boş kabul; Core org-members ayrı iş |
| Delete vs archive UX | UI'da “Arşivle” / “Kalıcı sil” ayrımı |
| Migration sıra | Branch head'ten sonra `0043_crm_todos` (mevcut `0042` sonrası) |
| Faz 2 genişlemesi | Faz 1'de customer/fair/import FK eklenmez |

---

## Backend İşleri

- [x] To-Do model / entity tasarla.
- [x] To-Do tablo migration dosyasını oluştur.
- [x] `organization_id` zorunlu olacak şekilde organizasyon izolasyonu kur.
- [x] `title`, `status`, `priority`, `category`, `created_by` alanlarını zorunlu yap.
- [x] `description`, `deadline`, `assignee_user_id`, `archived_at`, `completed_at` alanlarını opsiyonel yap.
- [x] Status enum değerlerini ekle:
  - `todo`
  - `in_progress`
  - `done`
  - `cancelled`
  - `archived`
- [x] Priority enum değerlerini ekle:
  - `low`
  - `normal`
  - `high`
  - `urgent`
- [x] Category enum değerlerini ekle (DB/API ASCII slug; TR label frontend'de):
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
- [x] Varsayılan priority değerini `normal` yap.
- [x] Varsayılan category değerini `genel_gorev` yap.
- [x] CRUD servislerini yaz.
- [x] Listeleme endpoint'ine filtreleri ekle:
  - `status`
  - `priority`
  - `category`
  - `assignee_user_id`
  - `created_by`
  - `is_overdue`
  - `include_archived`
  - `search`
- [x] `complete` aksiyonunu ekle.
- [x] `archive` aksiyonunu ekle.
- [x] Admin / owner için gerçek delete davranışını ekle.
- [x] Normal silme davranışında archive mantığını koru.
- [x] Overdue / gecikmiş hesaplamasını backend response içinde veya frontend'in hesaplayabileceği şekilde destekle.
- [x] Permission kontrollerini ekle:
  - `fair_crm.todos.read`
  - `fair_crm.todos.create`
  - `fair_crm.todos.update`
  - `fair_crm.todos.archive`
  - `fair_crm.todos.delete`

---

## API İşleri

- [x] `GET /todos` endpoint'i.
- [x] `GET /todos/{id}` endpoint'i.
- [x] `POST /todos` endpoint'i.
- [x] `PATCH /todos/{id}` endpoint'i.
- [x] `POST /todos/{id}/complete` endpoint'i.
- [x] `POST /todos/{id}/archive` endpoint'i.
- [x] `DELETE /todos/{id}` endpoint'i.

---

## Frontend İşleri

- [x] To-Do ana liste ekranı oluştur.
- [x] Liste ekranında şu kolonları göster:
  - Başlık
  - Durum
  - Öncelik
  - Kategori
  - Deadline / son tarih
  - Gecikmiş etiketi
  - Oluşturan kişi
  - Sorumlu kişi
  - Güncelleme tarihi
- [x] To-Do oluşturma formu oluştur.
- [x] To-Do düzenleme formu oluştur.
- [x] To-Do detay ekranı oluştur.
- [x] Sorumlu kişi alanını opsiyonel yap.
- [x] Category dropdown değerlerini ekle.
- [x] Priority dropdown değerlerini ekle.
- [x] Status dropdown değerlerini ekle.
- [x] Deadline geçmiş ve tamamlanmamış işlerde `gecikmiş` etiketi göster.
- [x] Liste filtrelerini ekle:
  - Durum
  - Öncelik
  - Kategori
  - Sorumlu kişi
  - Oluşturan kişi
  - Gecikmiş mi?
  - Arşivlenenler dahil mi?
  - Arama
- [x] Tamamlandı yap aksiyonu ekle.
- [x] Arşivle aksiyonu ekle.
- [x] Admin / owner kullanıcılar için gerçek delete aksiyonunu göster.
- [x] Yetkisi olmayan kullanıcıya delete aksiyonunu gösterme.

---

## Test İşleri

- [x] Organizasyon izolasyonu testi.
- [x] To-Do oluşturma testi.
- [x] To-Do listeleme testi.
- [x] To-Do detay testi.
- [x] To-Do güncelleme testi.
- [x] To-Do tamamlandı yapma testi.
- [x] To-Do arşivleme testi.
- [x] Admin / owner gerçek delete testi.
- [x] Yetkisiz delete engelleme testi.
- [x] Sorumlu kişi boş bırakılabiliyor testi.
- [x] Deadline geçmiş ve tamamlanmamış kayıt için gecikmiş etiketi testi.
- [x] `done` durumundaki kayıt için gecikmiş etiketi gösterilmemesi testi.
- [x] Category enum doğrulama testi.
- [x] Priority enum doğrulama testi.
- [x] Status enum doğrulama testi.
- [x] Liste filtreleri testi.
- [x] Search testi.

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

---

## Faz 1 Completion Note

**Tamamlanma tarihi:** 2026-07-06

**Kapanış commit'leri:**

- `41f5154` — docs: add organization-based todo module scope
- `752126b` — docs: add todo implementation plan and decisions
- `9a375bc` — feat: add todo backend crud foundation
- `484c479` — feat: add todo actions filters and role matrix
- `e389458` — feat: add todo frontend page and navigation

**Özet:**

- Görevler menüsü ana sidebar'a eklendi.
- Route: `/todos`
- Backend CRUD + complete/archive/delete çalışıyor.
- Role matrix eklendi.
- Frontend build başarılı.
- Kullanıcı smoke test yaptı: görev ekleme ve silme çalıştı.
- Faz 1 tamamlandı.

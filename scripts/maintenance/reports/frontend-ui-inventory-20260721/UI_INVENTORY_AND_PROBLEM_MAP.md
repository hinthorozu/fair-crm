# FAIR CRM Frontend — UI Envanteri ve Sorun Haritası

**Tarih:** 2026-07-21  
**Kapsam:** `frontend/src` tamamı (pages, components, auth, hooks, styles)  
**Kaynaklar:** `PROJECT_CONSTITUTION.md`, `docs/frontend/RESPONSIVE_UI_STANDARD.md`, ADR-028 / ADR-032 (`docs/DECISIONS.md`), `components/ui/*`  
**Not:** Bu aşamada refactor yok — sadece envanter.

---

## Ortak UI kataloğu (mevcut standart)

| Alan | Ortak altyapı | Konum |
|------|---------------|--------|
| Button | Class standard `.btn` / `.btn.primary\|secondary\|danger\|ghost\|link` (+ kebab alias) | `styles.css` (Button.tsx yok) |
| Input / Password | `TextInput`, `PasswordInput` | `components/ui/form/FormInputs.tsx` |
| TextArea | `TextareaInput` | aynı |
| Select | `SelectInput` | aynı |
| Checkbox / Radio | `CheckboxField`, `RadioField` | aynı |
| Form | `FormGrid`, `FormField`, `FormSection`, `FormActions`, `FormModal` | `components/ui/form/*` |
| Modal / Confirm | `Modal`, `ConfirmDialog`, `FormModal`, `Drawer` | `components/ui/` (ADR-028) |
| DataTable | `UniversalDataTable` → `WidthResponsiveDataTable` (+ `ServerDataTableFrame`) | `components/ui/` (ADR-032) |
| Pagination | `PaginationBar` + frame dual pagination | `components/Pagination.tsx`, `ServerDataTableFrame` |
| Filter | `FilterPanel` | `components/ui/FilterPanel.tsx` |
| Card | `Card` | `components/ui/Card.tsx` |
| Page header | `PageHeader`, `SectionHeader` | `components/ui/` |
| Layout / Shell | `AppLayout`, `AdminSystemLayout`, `DataIntegrationLayout`, `Breadcrumb`, `UserMenu` | `components/layout`, `admin`, `dataIntegration` |
| Alert / Toast | Ortak Toast **yok**; `.banner`, `EmptyState`, `LoadingState`, `Badge` | CSS + ui |
| Diğer | `Tabs`, `TruncatedText`, `TechnicalDetails`, `DetailFields`, `Badge` | `components/ui/` |

---

## Kategori özeti

Format: **UI türü → ortak altyapı → toplam kullanım (yaklaşık) → standart → standart dışı → dosyalar**

### 1. Button

| | |
|--|--|
| **Ortak** | `.btn` class standardı (ADR-032 §5); `Button.tsx` yok |
| **Standart kullanım** | Geniş: neredeyse tüm sayfa/action yüzeyleri `className="btn …"` |
| **Standart dışı** | Sidebar / collapse / icon-only `<button>` bazıları `.btn` kullanmaz (chrome; bilinçli olabilir) |
| **Dosyalar (örnek chrome)** | `SidebarCollapseButton.tsx`, `NavIcons` tüketicileri, bazı expand kontrolleri |

### 2. Input / TextBox

| | |
|--|--|
| **Ortak** | `TextInput`, `PasswordInput` |
| **Standart** | **14 dosya** import ediyor (~74 mention) |
| **Standart dışı (raw `<input`)** | **26 dosya** (~75 match) — form kit dışı |
| **Önemli local dosyalar** | `ImportWizardPage`, `DatabaseBackupsPage`, `TodosPage`, `ActivitiesPage`, `MailOperationsPage`, `ScraperRunHistoryPage`, `CustomerList`, `FairList`, `AdapterForm`, `FairBulkEmailWizard`, `FairEntitySelect`, `AdapterSelect`, `CustomerDetailPage`, `FairDetailPage`, `TodoDetailPage`, `FollowUpsPage`, `AdapterManagementPage`, `DataOperationsPage`, `DataOperationDuplicateResultPage`, `EnrichmentRunPanel`, `AdapterRunLogConsole`, `OutputFieldsSection`, `DuplicateGroupDetailView`, `CustomerCommunicationFieldList`, `UniversalDataTableSelection` (checkbox input), `FormInputs` (tanım) |

### 3. TextArea

| | |
|--|--|
| **Ortak** | `TextareaInput` |
| **Standart** | **11 dosya** import |
| **Standart dışı raw `<textarea`** | **3 dosya** |
| **Dosyalar** | `FormInputs.tsx` (tanım), `AdapterForm.tsx`, `DatabaseBackupsPage.tsx` |

### 4. Select

| | |
|--|--|
| **Ortak** | `SelectInput` + domain wrapper’lar (`FairEntitySelect`, `AdapterSelect`) |
| **Standart** | **11 dosya** `SelectInput` import |
| **Standart dışı raw `<select`** | **13 dosya** (~33 match) |
| **Dosyalar** | `ImportWizardPage`, `TodosPage`, `ActivitiesPage`, `ScraperRunHistoryPage`, `MailOperationsPage`, `CustomerList`, `FairList`, `ExcelMappingGrid`, `Pagination` (page size), `MailTemplatesPage`, `ScraperTestPage`, `FormInputs` (tanım) |

### 5. Checkbox / Radio

| | |
|--|--|
| **Ortak** | `CheckboxField`, `RadioField` (ADR-032 §4 — bare checkbox yasak) |
| **Standart** | CheckboxField **6 dosya**; RadioField **1 dosya** (`EnrichmentRunPanel`) |
| **Standart dışı** | `type="checkbox|radio"` **12 dosya** (~33 match) |
| **Dosyalar** | `ImportWizardPage`, `FairBulkEmailWizard`, `AdapterForm`, `DatabaseBackupsPage`, `UniversalDataTableSelection`, `DuplicateGroupDetailView`, `AdapterRunLogConsole`, `TodosPage`, `OutputFieldsSection`, `CustomerCommunicationFieldList`, `DataOperationsPage`, `FormInputs` (tanım) |

### 6. Form

| | |
|--|--|
| **Ortak** | `FormGrid` / `FormField` / `FormSection` / `FormActions` / `FormModal` |
| **Standart** | FormGrid **13**, FormField **14** dosya |
| **Standart dışı** | Birçok ekran hâlâ `<label>` + raw control + `.filters` / özel form markup (özellikle list filter ve wizard) |
| **İyi örnekler** | Entity formlar (`CustomerForm`, `FairForm`, `ActivityForm`, `ContactForm`, `ParticipationForm`, `SmtpAccountForm`, `MailTemplateForm`) |

### 7. Modal / Dialog / Confirmation

| | |
|--|--|
| **Ortak** | `Modal`, `ConfirmDialog`, `FormModal`, `Drawer` (ADR-028) |
| **Standart** | Modal ~**15**, ConfirmDialog ~**15** dosya |
| **Standart dışı** | `*Modal*.tsx` içinde shared import **olmayan** dosya: **0** |
| **Not** | Dirty-guard: `useReportFormDirty` / `useModalFormCancel` — entity formlarda kullanılıyor |

### 8. DataTable / Table

| | |
|--|--|
| **Ortak** | `UniversalDataTable` → `WidthResponsiveDataTable` (+ `ServerDataTableFrame`) |
| **Standart** | UniversalDataTable **27 dosya** |
| **Deprecated** | `ResponsiveDataTable` consumer: **0** (sadece tanım dosyası) |
| **Raw `<table`** | **4 dosya** (2 specialty + 2 engine tanımı) |
| **Specialty (ADR-032 istisna / scroll-only)** | `ImportWizardPage` (sample + mapping), `ExcelMappingGrid` |
| **Engine** | `DataTable.tsx`, `WidthResponsiveDataTable.tsx` |

### 9. Pagination

| | |
|--|--|
| **Ortak** | `PaginationBar` + `ServerDataTableFrame` dual pagination |
| **Standart** | PaginationBar doğrudan import **2** (frame + duplicate result); çoğu liste `table=` / outer frame ile geliyor |
| **Standart dışı** | Bilinen ayrı pagination implementasyonu yok |

### 10. Filter / Toolbar

| | |
|--|--|
| **Ortak** | `FilterPanel` |
| **Standart** | **6 dosya**: Activities, Todos, FollowUps, ScraperRunHistory, CustomerList, FairList |
| **Standart dışı** | `className`…`filters` ama **FilterPanel import yok**: **9 dosya** |
| **Dosyalar** | `ImportWizardPage`, `AdapterManagementPage`, `CustomerDetailPage`, `FairDetailPage`, `TodoDetailPage`, `MailOperationsPage`, `MailTemplatesPage`, `DataOperationDuplicateResultPage`, `ServerDataTableFrame` (toolbar-filters wrapper — frame parçası) |

### 11. Card

| | |
|--|--|
| **Ortak** | `Card` component |
| **Standart** | **12 dosya** import |
| **Standart dışı / karışık** | Birçok yerde bare `className="card"` (component’siz) — yüzey token’ı kullanıyor ama `Card` API’si değil |

### 12. PageHeader

| | |
|--|--|
| **Ortak** | `PageHeader`, `SectionHeader` |
| **Standart** | PageHeader **25 dosya** — list/admin sayfalarında güçlü adoption |
| **Standart dışı** | Nadir; bazı nested paneller `SectionHeader` veya custom `h3` kullanır |

### 13. Layout / Shell

| | |
|--|--|
| **Ortak** | `AppLayout`, `AdminSystemLayout`, `DataIntegrationLayout` |
| **Standart** | Tek shell yolu (`App.tsx` → layout’lar) |
| **Sorun alanı** | Nested admin/DI rail + content shrink (önceki responsive iş); chrome CSS karmaşıklığı |

### 14. Alert / Toast

| | |
|--|--|
| **Ortak Toast** | **Yok** |
| **Fiili pattern** | `.banner success\|error\|info\|warning`, `EmptyState`, `LoadingState`, `Badge` |
| **Ad-hoc toast** | `MailOperationsPage` (local state → banner), `DataIntegrationImportsPage` (`.import-toast`) |
| **CSS** | `.import-toast.success` |

### 15. Diğer tekrarlanan UI

| Yapı | Durum |
|------|--------|
| `Tabs` | Shared var; tab’lı detail sayfalarında kullanılıyor |
| `Badge` | Yaygın status chip |
| `TruncatedText` / `TechnicalDetails` | ADR-032 uzun/teknik alan standardı — kısmi adoption |
| `EmptyState` / `LoadingState` | Listelerde yaygın |
| `DetailFields` | Detail sayfa alanları |
| Actions menu (kebab) | `MailOperationActionsMenu`, `MailTemplateActionsMenu` — domain-local, shared menu primitive yok |

---

## Ortak standardı ezen / zayıflatan yapılar

### A. Component / JSX sapmaları (yüksek etki)

1. **Raw form controls** (en büyük gap) — list filter + wizard + scraper + backups hâlâ native `<input|select|textarea|checkbox>`.
2. **FilterPanel adoption düşük** — sadece 6 ekran; 9+ ekran local `.filters` toolbar.
3. **RadioField neredeyse kullanılmıyor** — sadece Enrichment.
4. **Toast yok** — 2 ekranda ad-hoc banner/toast class.
5. **Card component vs `.card` class** — çift yol.
6. **Specialty tables** — Import Wizard / Excel grid (bilinçli scroll-only istisna; list standardı değil).

### B. CSS hotspot’ları (`styles.css`)

| Risk | Ne |
|------|-----|
| `overflow-x: auto` | Birkaç yerde hâlâ var (scroll-only istisna + legacy) |
| `table-layout: fixed` | Width-responsive live table için bilinçli; page-local backups fixed **temizlendi** |
| `word-break: break-all` | `.text-mono` / `.detail-list .mono` — tablo hücrelerinde olmamalı (ADR-032 §8.2) |
| Page-local class’lar | `.import-toast`, çeşitli `*-filters`, scraper/admin chrome |
| Legacy card-stack CSS | Non–width-responsive `table-wrap` için hâlâ duruyor (DataTableShell etkilenir) |

### C. Mimari notlar (iyileştirme adayı, şimdi refactor yok)

| Konu | Durum |
|------|--------|
| Button primitive | Class-only; React `Button` yok — tutarlı ama variant API dağınık |
| Toast / Alert | Shared primitive eksik |
| FilterPanel | Listelerin çoğuna henüz uygulanmamış |
| Form kit | Entity CRUD formlarda güçlü; filter/wizard’da zayıf |
| DataTable | Liste ekranlarında güçlü adoption; specialty grid’ler ayrı |

---

## Sorun haritası (öncelik — refactor yok, sadece yön)

| Öncelik | Problem | Etki | Önerilen sonraki adım (ileride) |
|--------|---------|------|----------------------------------|
| P0 | Raw filter controls + local `.filters` | Responsive/DoD ve form standardı kırılıyor | FilterPanel + Form kit’e taşı |
| P0 | Bare checkbox/radio | ADR-032 §4 ihlali | CheckboxField/RadioField |
| P1 | Toast/banner dağınık | UX tutarsızlığı | Shared `Banner`/`Toast` |
| P1 | Card dual path | Token drift | `Card` zorunlu veya class deprecate |
| P2 | TruncatedText/TechnicalDetails kısmi | Uzun UUID/URL taşması riski | Teknik kolon audit |
| P2 | Legacy non-WR table CSS | DataTableShell specialty etkilenir | CSS daralt |
| P3 | Button chrome without `.btn` | Küçük tutarsızlık | Sidebar/icon button variant |

---

## Sağlıklı alanlar (koru)

- **Modal ekosistemi** ADR-028’e uyumlu; `*Modal*.tsx` hepsi shared shell kullanıyor.
- **UniversalDataTable** listelerde varsayılan; `ResponsiveDataTable` consumer yok.
- **PageHeader** çoğu product sayfada kullanılıyor.
- **Entity formlar** FormGrid/FormField kit’inde.

---

## Artefact’lar

- Script: `scripts/maintenance/inventory_frontend_ui.py`
- Ham JSON: `scripts/maintenance/reports/frontend-ui-inventory-20260721/inventory.json`
- Ham REPORT: `scripts/maintenance/reports/frontend-ui-inventory-20260721/REPORT.md`
- Bu özet: `scripts/maintenance/reports/frontend-ui-inventory-20260721/UI_INVENTORY_AND_PROBLEM_MAP.md`

_Commit/push yapılmadı. Refactor yapılmadı._

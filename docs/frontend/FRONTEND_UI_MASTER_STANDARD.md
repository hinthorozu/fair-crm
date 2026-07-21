# FAIR CRM — Frontend UI Master Standard

> **FRONTEND UI ÜZERİNDE HERHANGİ BİR DEĞİŞİKLİK YAPMADAN ÖNCE BU DOSYA OKUNMAK ZORUNDADIR.**

**Status:** Canonical / binding master standard  
**Scope:** `fair-crm/frontend` production UI  
**Audience:** All AI agents and human developers working on frontend UI  
**Related (supporting, not superseding):** [UI_DESIGN_SYSTEM.md](UI_DESIGN_SYSTEM.md), [RESPONSIVE_UI_STANDARD.md](RESPONSIVE_UI_STANDARD.md), ADR-032 / ADR-034 in [docs/DECISIONS.md](../DECISIONS.md)

Bu dosya, FAIR CRM frontend UI için **tek ve ana** kaynaktır. Geçmiş sohbet, sprint notu veya yerel alışkanlık bu dosyanın yerine geçmez. Frontend UI konusunda başka bir doküman bu dosyayla çelişirse **bu dosya kazanır** (bkz. §26).

---

## 1. Tek UI / Design System

FAIR CRM frontend **tek bir UI / Design System** kullanır.

- Shared primitives: `frontend/src/components/ui/` (+ layout: `frontend/src/components/layout/`)
- Design tokens: `frontend/src/styles.css` (`:root`)
- Visible copy: Turkish, `frontend/src/labels/`

Aynı ürün içinde paralel “mini design system”, sayfa-özel chrome veya kopya control ailesi **yasaktır**.

---

## 2. İkinci / ad-hoc component yasağı

Aynı işi yapan ikinci veya ad-hoc component **oluşturulamaz**.

Örnekler (yasak):

- İkinci button ailesi
- Sayfa-local modal footer / confirm pattern
- Liste için özel responsive table motoru
- “Bu ekranda hızlı olsun diye” raw control

Mevcut pattern yetersizse önce mevcut shared component **genişletilir** (variant / prop). Yeni shared component yalnızca §23 koşullarında açılır.

---

## 3. Mevcut ortak component zorunluluğu

Ortak component varsa kullanımı **zorunludur**.

“Class token’ı kopyalayıp raw element kullanmak” ortak component kullanımı sayılmaz. Consumer kod shared API’yi (`Button`, `CheckboxField`, `Banner`, `PageShell`, …) kullanmalıdır.

Allowlist / specialty istisnaları yalnızca belgelenmiş ve gerekçeli olabilir (bkz. §6). `"specialty"` tek başına gerekçe değildir.

---

## 4. Tek standarda bağlı alanlar

Aşağıdaki alanların **tamamı** tek standarda bağlıdır. Yeni ekran veya değişiklik bu aile dışına çıkamaz.

| Alan | Canonical giriş |
|------|-----------------|
| Button | `components/ui/Button.tsx` + `.btn*` tokens |
| IconButton | `components/ui/IconButton.tsx` |
| Input | `TextInput` in `components/ui/form/FormInputs.tsx` |
| PasswordInput | `PasswordInput` in `FormInputs.tsx` |
| Textarea | `TextareaInput` in `FormInputs.tsx` |
| Select | `SelectInput` in `FormInputs.tsx` |
| Combobox / EntitySelect | Domain wrappers (`FairEntitySelect`, `AdapterSelect`, …) — raw listbox yeniden yazılmaz |
| Checkbox | `CheckboxField` in `FormInputs.tsx` |
| Radio | `RadioField` in `FormInputs.tsx` |
| Switch | Shared Switch yok → ad-hoc toggle **yasak**; `CheckboxField` veya ADR + shared kit |
| FieldError | `components/ui/form/FieldError.tsx` |
| Banner / Alert | `components/ui/Banner.tsx` |
| Card | `components/ui/Card.tsx` |
| Badge / Status | `components/ui/Badge.tsx` |
| Table | `UniversalDataTable` → `WidthResponsiveDataTable` (+ `ServerDataTableFrame`) |
| Table links / actions | `TableEntityLink`, `TableRowActions` |
| Pagination | `PaginationBar` via `ServerDataTableFrame` (dual top+bottom default) |
| Modal | `components/ui/Modal.tsx` |
| FormModal | `components/ui/form/FormModal.tsx` |
| ConfirmDialog | `components/ui/ConfirmDialog.tsx` |
| Drawer | `components/ui/Drawer.tsx` |
| Dropdown / Menu | `IconButton` + floating position helper pattern |
| Tooltip | Shared / title truncation patterns (`TruncatedText` where applicable) |
| LoadingState | `components/ui/LoadingState.tsx` |
| EmptyState | `components/ui/EmptyState.tsx` |
| Filter / Toolbar | `FilterPanel` + `ServerDataTableFrame` toolbar slot |
| PageHeader | `components/ui/PageHeader.tsx` |
| Navigation | `AppLayout` / admin & data-integration layouts |
| NavLink | `components/layout/NavLink.tsx` |
| PageShell | `components/ui/PageShell.tsx` |

Detay katalog ve token listesi için [UI_DESIGN_SYSTEM.md](UI_DESIGN_SYSTEM.md) destekler; çelişkide **bu master** geçerlidir.

---

## 5. Raw / ad-hoc kullanım kuralı

Mevcut ortak component ile çözülebiliyorsa aşağıdaki **oluşturulamaz**:

- raw `<button>` (shared `Button` / `IconButton` / `.btn` kit dışında)
- raw `<input>`
- raw `<textarea>`
- raw `<select>`
- raw checkbox / radio UI (`type="checkbox|radio"` consumer’da)
- ad-hoc card (`className="card"` spam)
- ad-hoc modal footer (bare `.modal-actions` / modal içinde serbest `form-actions` chrome)
- ad-hoc banner / error / loading / empty state
- ad-hoc table actions
- ad-hoc navigation / page shell

**Anlamı:** “CSS class’ını biliyorum” ≠ “shared component kullandım”. Consumer shared component API’sini kullanır; kit dosyaları token’ı uygular.

Belgelenmiş specialty allowlist dışındaki raw kullanım **FAIL**’dir.

---

## 6. Specialty component politikası

**“Specialty” tek başına istisna gerekçesi değildir.**

Specialty UI yalnızca şu koşulların **hepsi** sağlanınca kabul edilir:

1. Generic / shared componentin **neden yeterli olmadığı** yazılı olarak açıklanır.
2. Uygulama **design token** kullanır (magic color/spacing yok).
3. Typography / spacing / colors / radius / focus sistemine uyar.
4. Responsive’dır (fluid; §14–§16).
5. Genel FAIR CRM görünümünden kopmaz.
6. Inventory allowlist + gerekirse targeted test / gate ile korunur.

Specialty örnekleri (yine de token + görünüm disiplini zorunlu): Import mapping grid’leri, async entity combobox chrome, auth login shell (PageShell dışı belgelenmiş istisna).

---

## 7. Design token standardı

Aşağıdakiler merkezi sistemden (`frontend/src/styles.css` `:root`) gelmelidir:

- typography
- spacing
- colors / surfaces
- border
- radius
- shadow
- focus
- hover
- active
- disabled
- loading
- validation
- control height
- container / page width

**Sayfa bazında rastgele magic value kullanılmamalıdır** (`padding: 13px`, `#3b82f6`, rastgele `max-width: 1234px`, yeni media-query px’leri, vb.).

### Mevcut token özeti (kaynak: `styles.css`)

| Kategori | Örnekler |
|----------|----------|
| Surfaces | `--bg`, `--surface`, `--surface-raised`, `--surface-sunken`, `--surface-overlay` |
| Text | `--text`, `--muted` |
| Borders | `--border`, `--border-strong` |
| Semantic | `--primary*`, `--success*`, `--warning*`, `--danger*`, `--info*`, `--neutral*` |
| Type | `--font-sans`, `--font-mono`, `--text-xs`…`--text-3xl`, `--leading-*`, `--weight-*` |
| Spacing | `--space-1`…`--space-12`, `--section-gap`, `--form-gap` |
| Layout | `--page-padding` (`clamp`), `--page-content-max-width` |
| Form widths | `--form-width-narrow` (28rem), `--form-width-standard` (48rem), `--form-width-wide` (72rem), `--form-width-full` |
| Controls | `--control-height*`, `--control-padding-x`, `--control-radius`, `--check-size` |
| Radius / shadow | `--radius-sm|radius|radius-lg`, `--shadow-sm|shadow|shadow-lg` |
| Focus / disabled | `--focus-ring`, `--focus-ring-danger`, `--disabled-opacity` |
| Breakpoints | `--bp-mobile` 390, `--bp-tablet` 768, `--bp-laptop` 1024, `--bp-desktop` 1440 |

Yeni token yalnızca bilinçli sistem kararıyla eklenir; bu master + `styles.css` birlikte güncellenir.

---

## 8. Checkbox / Radio standardı

Browser default / native çıplak checkbox-radio görünümü **FAIR CRM standardı değildir**.

Zorunlu giriş:

- `CheckboxField`
- `RadioField`

(`frontend/src/components/ui/form/FormInputs.tsx`)

Tek sistem şunları kapsar:

- boyut (`--check-size` / control tokens)
- checked state
- border
- radius
- hover
- focus-visible
- disabled
- label spacing
- vertical alignment

### Label ayrılmazlığı (bağlayıcı)

Checkbox/radio ile label **birbirinden kopamaz**.

Control + label aynı satırda / aynı etkileşim kümesinde kalır.  
Örnek FAIL: checkbox solda, “Destekleniyor” yazısı ekranın diğer ucunda — bu responsive PASS değildir; **UI hatasıdır**.

Bare `type="checkbox|radio"` consumer kodda yasaktır (kit tanımı dışında).

---

## 9. Form standardı

Her formda aşağıdaki alanlar tek standarda bağlıdır:

- label
- control
- helper / error
- spacing
- required indicator
- validation
- action area
- width
- responsive columns

Canonical primitives:

- `FormField` / `FormGrid` / `FormSection` / `FormActions`
- Controls: `TextInput`, `PasswordInput`, `TextareaInput`, `SelectInput`, `CheckboxField`, `RadioField`
- Errors: `FieldError` (+ `aria-describedby` / `aria-invalid`)

Formlar viewport boyunca **rastgele yayılmamalıdır**.

### Form genişlik niyetleri

Token + class (eşdeğer):

| Intent | Token | Class | Tipik kullanım |
|--------|-------|-------|----------------|
| **narrow** | `--form-width-narrow` (28rem) | `.crm-form--narrow` / `.form-width-narrow` | Kısa ayar, tek kolon, basit dialog formu |
| **standard** | `--form-width-standard` (48rem) | `.crm-form--standard` / `.form-width-standard` | Varsayılan entity CRUD |
| **wide** | `--form-width-wide` (72rem) | `.crm-form--wide` / `.form-width-wide` | Çok alanlı / 3 kolonlu yoğun formlar |
| **full** | `--form-width-full` (100%) | `.crm-form--full` / `.form-width-full` | Specialty yoğun grid; bilinçli seçim |

`FormGrid`: varsayılan responsive 3 → 2 → 1 kolon (desktop / tablet / mobile). Sabit px kolon genişlikleriyle taşırma yasaktır.

Modal içi form action’ları modal `footer` chrome’una aittir; rastgele ad-hoc footer üretilmez (ADR-028 dirty-guard kuralları geçerlidir).

---

## 10. Button standardı

Variant ve size sistemi **tek** olmalıdır.

### Variants

| Variant | Rol |
|---------|-----|
| `primary` | Ana CTA |
| `secondary` | Varsayılan / ikincil aksiyon |
| `ghost` (tertiary) | Düşük vurgu |
| `danger` | Yıkıcı aksiyon |
| `link` | Metin/link aksiyonu (`danger` link için prop) |
| icon-only | `IconButton` (text `Button` değil) |

### Sizes

`sm` | `md` (default) | `lg`

Aynı önem seviyesindeki butonlar **farklı görünmemelidir**. Sayfa-özel renkli div-button, yeni “cta” class’ı veya paralel button CSS’i yasaktır.

Loading: `Button` `loading` prop (`aria-busy`); ad-hoc “Yükleniyor…” button hack’i yasak.

Critical actions mobilde gizlenemez / yatay scroll arkasına atılamaz.

---

## 11. Table standardı

Her tablo aşağıdaki açılardan tek sistem içindedir:

- header
- density
- column spacing
- alignment
- numeric alignment
- wrapping / truncation
- actions
- filters
- toolbar
- pagination
- responsive behavior

**Entry point:** `UniversalDataTable` → `WidthResponsiveDataTable`  
**Frame:** `ServerDataTableFrame` (toolbar + dual pagination)

Kurallar:

- Actions kolonu **asla** sortable değildir; diğer data kolonları varsayılan sortable (ADR-019).
- Kolon dizisi sırası = responsive öncelik; daralınca sağdan gizlenir, child row’da görünür.
- Teknik alanlar (`priority: "technical"`) ana satıra konmaz.
- Default horizontal page scroll **kapalıdır**; `table-wrap--scroll-only` yalnızca bilinçli specialty.
- Column squeeze / `word-break: break-all` hack yasak.
- Dual top+bottom pagination varsayılandır.

**Tablo yalnızca overflow vermiyor diye doğru kabul edilmez.** Okunabilirlik, hiyerarşi, action erişimi ve child-row davranışı da PASS koşuludur.

Detay: [RESPONSIVE_UI_STANDARD.md](RESPONSIVE_UI_STANDARD.md) §8 — çelişkide bu master.

---

## 12. Modal / Dialog standardı

Şunlar tek sistem kullanır:

- title
- body
- footer
- actions
- focus
- keyboard
- mobile width
- desktop width
- overflow

Canonical:

- `Modal`
- `FormModal`
- `ConfirmDialog`
- `Drawer`

Davranış:

- Desktop: centered
- Tablet: wide
- Mobile: full-width bottom-sheet tarzı + sticky footer
- Focus trap; dirty formda backdrop/Escape ile sessiz dismiss yok (ADR-028)
- Ad-hoc backdrop / custom footer chrome yasak

---

## 13. Page standardı

Production ekranların temel yapısı:

```text
PageShell
  → PageHeader
  → Toolbar / Filters
  → Content
```

(İsteğe bağlı: summary cards, detail sections, modal/drawer overlays.)

Yeni route kendi kafasına göre page chrome **oluşturamaz**.

- Her in-app production page: `PageShell`
- Title/actions: `PageHeader`
- List filters: `FilterPanel`
- Auth Login: belgelenmiş PageShell istisnası (brand shell)

`PageShell fullWidth` yalnızca specialty yoğun layout’lar içindir (ör. Import Wizard). Varsayılan içerik `--page-content-max-width` ile clamp edilir.

---

## 14. Responsive ana kural

FAIR CRM birkaç sabit çözünürlüğe göre tasarlanmaz.

**Minimum desteklenen viewport genişliğinden itibaren üst sınır olmadan** düzgün çalışmalıdır.

Kullanılacak yaklaşım:

- fluid sizing
- flex
- grid
- `minmax()`
- `clamp()`
- `max-width`
- controlled containers
- responsive wrapping

Yasak / anti-pattern:

- “Sadece 1440’te güzel”
- Device-specific tek-off CSS dosyaları
- Ultrawide’de içeriğin seyrek/kırık yayılması (content clamp unutulması)
- Overflow’u “çözüm” sanmak

List **tables** sabit breakpoint layout’una geçmez; container width kullanır (§11).

---

## 15. Breakpoint politikası

Mevcut standart breakpoint yapısı (CSS tokens + smoke hedefleri):

| Tier | Width | Smoke target | Token |
|------|-------|--------------|-------|
| Mobile | `< 768px` | 390px | `--bp-mobile` |
| Tablet | `768px–1023px` | 768px | `--bp-tablet` |
| Laptop | `≥ 1024px` | 1024px | `--bp-laptop` |
| Desktop polish | `≥ 1440px` | 1440px | `--bp-desktop` |

**Yeni magic breakpoint rastgele eklenemez.**

Yeni sistem breakpoint’i gerekiyorsa karar **ayrıca belgelenir** (ADR) ve bu master + `styles.css` tokens birlikte güncellenir.

---

## 16. Responsive test kuralı

Sadece birkaç sabit viewport PASS olması **yeterli değildir**.

Kontrol edilmelidir:

- horizontal overflow
- clipping
- overlap
- stretched controls
- broken grid
- toolbar wrapping
- sidebar / header
- modal / form widths
- table actions
- card layout
- text overflow
- visual hierarchy

Breakpoint varsa şunlar kontrol edilir:

- breakpoint − 1
- breakpoint
- breakpoint + 1

Ultrawide ekranlarda da layout doğrulanır.  
**Üst viewport limiti koyulmaz.**

Smoke hedefleri (minimum set): 390 / 768 / 1024 / 1440 + ultrawide + table container resize.

---

## 17. Görsel kalite kuralı

Aşağıdakiler **tek başına** UI PASS değildir:

- build PASS
- TypeScript PASS
- inventory PASS
- overflow = 0
- responsive smoke PASS
- ortak component kullanılması

Gerçek ekranda ayrıca kontrol edilir:

- alignment
- whitespace
- density
- hierarchy
- typography
- field sizing
- action placement
- table readability
- responsive balance

**Görsel olarak kötü bir ekran teknik testleri geçse bile FAIL kabul edilir.**

---

## 18. Gerçek Visual QA zorunluluğu

Büyük UI değişikliklerinde route **gerçek render** edilmelidir.

Yeterli değildir:

- yalnızca grep
- yalnızca source-code incelemesi
- yalnızca DOM ölçümü / inventory script

Mobile / tablet / desktop / ultrawide görünüm gerçekten değerlendirilmelidir.

Parametreli / detail route’lar da gerçek veya test verisiyle kapsamda olmalıdır.

Kanıt için mevcut tooling (ör. `frontend/scripts/capture-ui-evidence.mjs`) kullanılabilir; tooling yokluğu Visual QA’yı iptal etmez.

---

## 19. Accessibility standardı

Kontrol listesi (minimum):

- `aria-label` (özellikle icon-only kontroller)
- `aria-current` (aktif navigasyon)
- label / control ilişkileri (`FormField`, wrapping label, `htmlFor`)
- keyboard navigation
- `focus-visible` (token’lı focus ring)
- disabled semantics
- semantic `button` / `link` (div-as-button yasak)
- modal focus trap + keyboard (Escape / dirty-guard kuralları)

Icon-only kontrolde görünür metin yoksa `aria-label` **zorunludur**.

---

## 20. P0 / P1 / P2 / P3 / FINAL terimleri

Bu terimler **UI governance gate** seviyeleridir (Product Vision business P0/P1/P2 ile karıştırılmamalıdır).

Gate script:

```powershell
python scripts/maintenance/inventory_frontend_ui.py --gate P0
python scripts/maintenance/inventory_frontend_ui.py --gate P1
python scripts/maintenance/inventory_frontend_ui.py --gate P2
python scripts/maintenance/inventory_frontend_ui.py --gate P3
python scripts/maintenance/inventory_frontend_ui.py --gate FINAL
python scripts/maintenance/inventory_frontend_ui.py --gate ALL
```

| Gate | Anlam |
|------|--------|
| **P0** | Temel legacy / raw / ad-hoc UI temizliği (raw filter/form controls, bare checkbox/radio, FilterPanel’sız local filters) |
| **P1** | Banner / Card / feedback container standardizasyonu |
| **P2** | `FieldError`, `TableEntityLink`, `TableRowActions`, `EmptyState`, `LoadingState` ve ilgili content/form/table yardımcı patternleri |
| **P3** | `IconButton`, `PageShell`, `NavLink`, Sidebar, Navigation, shell/chrome/layout standardizasyonu |
| **FINAL** | Sistem çapında son UI governance / design-system kontrolü (residual chrome, tokens, a11y, routes, breakpoint hijyeni) |

**Açık kural:** P0–P3 / FINAL PASS olması tek başına görsel kaliteyi kanıtlamaz.  
**Gerçek Visual QA ayrıca zorunludur** (§17–§18).

---

## 21. Definition of Done

Bir frontend UI işi aşağıdaki maddeler sağlanmadan **DONE değildir**:

- [ ] Bu master standarda uyuyor
- [ ] Mevcut ortak componentler kullanıldı
- [ ] Gereksiz raw / ad-hoc UI yok
- [ ] Design tokens kullanıldı
- [ ] Responsive doğrulandı (§14–§16)
- [ ] Breakpoint boundary problemi yok
- [ ] Overflow / overlap / clipping yok
- [ ] Form / control width doğru (§9)
- [ ] Visual hierarchy doğru (§17)
- [ ] Gerçek Visual QA geçti (§18)
- [ ] Accessibility regression yok (§19)
- [ ] `npm run build` PASS
- [ ] İlgili UI tests PASS
- [ ] Inventory / gate kontrolleri PASS (`inventory_frontend_ui.py` ilgili gate)

---

## 22. Yeni ekran ekleme kuralları

Yeni production route:

1. `PageShell` kullanır
2. Standart `PageHeader` kullanır
3. Ortak form controls kullanır
4. Ortak buttons kullanır
5. Ortak feedback states kullanır (`Banner`, `EmptyState`, `LoadingState`, `FieldError`)
6. Mevcut table sistemini kullanır (`UniversalDataTable` …)
7. Fluid responsive tasarlanır
8. Visual QA görür

Route mount (`App.tsx`) + smoke coverage beklentisi governance gate’leriyle uyumlu olmalıdır.

---

## 23. Yeni component ekleme kuralları

1. Önce mevcut component aranır (`components/ui/`, layout, domain select wrappers).
2. Mevcut component variant / prop ile genişletilebiliyorsa **ikinci component oluşturulmaz**.
3. Yeni shared component yalnızca:
   - gerçekten yeni,
   - tekrar kullanılabilir,
   - tek design system’e eklenen  
   bir pattern ise oluşturulur.
4. Yeni shared component token’lara bağlanır; dokümantasyon (bu master ve/veya UI_DESIGN_SYSTEM) güncellenir.
5. Consumer’a “geçici local primitive” bırakılmaz.

---

## 24. AI çalışma talimatı

Repo üzerinde çalışan AI:

**BU DOSYAYI OKUMADAN FRONTEND UI KODU DEĞİŞTİREMEZ.**

AI:

- mevcut UI mimarisini korumalıdır
- yeni inconsistency oluşturmamalıdır
- edge-case viewport’ları düşünmelidir
- bariz görsel UI risklerini kullanıcı söylemeden fark etmelidir

AI şu sonuçlara **varamaz**:

- “build geçti = UI tamam”
- “overflow yok = responsive”
- “shared component var = görünüm doğru”
- “inventory PASS = Visual QA PASS”

---

## 25. Yazılımcı çalışma talimatı

Bu dosyadaki kurallar **code review kabul kriteridir**.

Reviewer / author:

- §4–§5 ihlali → değişiklik reddedilir veya düzeltilmeden merge edilmez
- Visual QA’sız büyük UI PR → incomplete
- Magic breakpoint / magic token → incomplete
- “geçici raw control” → incomplete (allowlist + gerekçe yoksa)

---

## 26. Çelişki politikası

- Frontend UI konusunda başka doküman bu dosyayla çelişirse **bu dosya ana kaynak** kabul edilir.
- Daha yeni bilinçli bir ADR bu standardı değiştirirse **bu master dosya da aynı değişiklikle güncellenmelidir**.
- Supporting docs (`UI_DESIGN_SYSTEM.md`, `RESPONSIVE_UI_STANDARD.md`) uygulama detayı sağlar; master’ı sessizce override edemez.

---

## 27. Ana ilke

**TEK ÜRÜN — TEK DESIGN SYSTEM — TEK COMPONENT AİLESİ — TEK RESPONSIVE YAKLAŞIM.**

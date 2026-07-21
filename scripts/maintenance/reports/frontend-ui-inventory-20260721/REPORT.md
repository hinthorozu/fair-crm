# FAIR CRM Frontend UI Inventory

Read-only audit of `frontend/src` against PROJECT_CONSTITUTION + ADR-028/032 + `docs/frontend/RESPONSIVE_UI_STANDARD.md`.

## P0 standardization gate

- **PASS:** YES
- **Total P0 violations:** 0
- Bare checkbox/radio (outside FormInputs): **0**
- Local `.filters` without FilterPanel: **0**
- Raw `<input|select|textarea>` (excl. specialty/domain allowlist): **0**
- Allowlist: `frontend/src/components/AdapterSelect.tsx`, `frontend/src/components/FairEntitySelect.tsx`, `frontend/src/components/imports/ExcelMappingGrid.tsx`, `frontend/src/components/ui/form/FormInputs.tsx`

## P1 standardization gate

- **PASS:** YES
- **Total P1 violations:** 0
- Bare alert/toast class tokens (`banner`/`toast`/`import-toast`): **0**
- Bare `card` class token on raw elements: **0**
- Intentional specialty layouts (non-notification `*-banner`): **1**

## P2 standardization gate

- **PASS:** YES
- **Total P2 violations:** 0
- Bare `form-error` class: **0**
- Legacy `link-button`: **0**
- Ad-hoc emptyState `<p className="text-muted">`: **0**
- Ad-hoc page loading `<p>Yükleniyor…`: **0**
- Bare table/list action wrappers (not TableRowActions): **0**
- Intentional exceptions: **2**

## P3 standardization gate

- **PASS:** YES
- **Total P3 violations:** 0
- Bare icon-button class tokens: **0**
- `login-form-error`: **0**
- Bare nav-link class markup (outside NavLink): **0**
- Pages missing PageShell: **0**
- Layouts missing NavLink: **0**
- Intentional exceptions: **4**

## FINAL standardization gate

- **PASS:** YES
- **Total FINAL violations:** 0
- Bare `field-error` (outside FieldError/FormField): **0**
- Bare `modal-actions`: **0**
- `form-actions` inside Modal/FormModal (non-allowlist): **0**
- Legacy CSS breakpoints (not ADR set): **0**
- Icon buttons missing aria-label: **0**
- Prior gates failed: **NO**
- Breakpoints found: 767, 768, 1023, 1024, 1440
- Intentional exceptions: **5**

### P1 details

**Intentional exceptions** (1):
- `frontend/src/pages/ImportWizardPage.tsx:1217` (specialty_banner_layout) — `<div className="import-complete-banner">`

### P2 details

**Intentional exceptions** (2):
- `frontend/src/components/AdapterSelect.tsx:0` (domain_combobox_loading) — `inline combobox loading text (not page LoadingState)`
- `frontend/src/components/FairEntitySelect.tsx:0` (domain_combobox_loading) — `inline combobox loading text (not page LoadingState)`

### P3 details

**Intentional exceptions** (4):
- `frontend/src/components/ui/WidthResponsiveDataTable.tsx:280` (table_expand_placeholder_span) — `<span className="table-expand-btn">+</span>`
- `frontend/src/components/ui/WidthResponsiveDataTable.tsx:299` (table_expand_placeholder_span) — `<span className="table-expand-btn">+</span>`
- `frontend/src/components/mail_templates/MailTemplateActionsMenu.tsx:0` (labeled_actions_menu) — `text trigger (not icon kebab) — intentional`
- `frontend/src/pages/LoginPage.tsx:0` (auth_shell) — `login brand shell outside AppLayout/PageShell — intentional`

### FINAL details

**Intentional exceptions** (5):
- `frontend/src/**/FairBulkEmailWizard.tsx:0` (in_form_modal_actions) — `multi-action form/wizard keeps form-actions in body`
- `frontend/src/**/FormActions.tsx:0` (in_form_modal_actions) — `multi-action form/wizard keeps form-actions in body`
- `frontend/src/**/MailTemplateTestEmailPanel.tsx:0` (in_form_modal_actions) — `multi-action form/wizard keeps form-actions in body`
- `frontend/src/**/ManualTaskMailModal.tsx:0` (in_form_modal_actions) — `multi-action form/wizard keeps form-actions in body`
- `frontend/src/**/TodoWorklistActivityModal.tsx:0` (in_form_modal_actions) — `multi-action form/wizard keeps form-actions in body`

## Shared catalog

- `components/ui`: Badge.tsx, Banner.tsx, Breadcrumb.tsx, Card.tsx, ConfirmDialog.tsx, DataTable.tsx, DetailFields.tsx, Drawer.tsx, EmptyState.tsx, FieldError.tsx, FilterPanel.tsx, FormActions.tsx, FormField.tsx, FormField.tsx, FormGrid.tsx, FormInputs.tsx, FormModal.tsx, FormSection.tsx, IconButton.tsx, LoadingState.tsx, Modal.tsx, PageHeader.tsx, PageShell.tsx, ResponsiveDataTable.tsx, SectionHeader.tsx, ServerDataTableFrame.tsx, TableEntityLink.tsx, TableRowActions.tsx, Tabs.tsx, TechnicalDetails.tsx, TruncatedText.tsx, UniversalDataTable.tsx, UniversalDataTableSelection.tsx, WidthResponsiveDataTable.tsx
- Form kit: FieldError.tsx, FormActions.tsx, FormField.tsx, FormGrid.tsx, FormInputs.tsx, FormModal.tsx, FormSection.tsx
- Layout: AppLayout.tsx, NavIcons.tsx, NavLink.tsx, SidebarCollapseButton.tsx, SidebarTooltip.tsx, UserMenu.tsx
- Nested shells: components/admin/AdminSystemLayout.tsx, components/dataIntegration/DataIntegrationLayout.tsx

## Category summary

| UI türü | Ortak altyapı | Toplam hit | Standart | Standart dışı | Standart dosya # | Standart dışı dosya # |
|---|---|---:|---:|---:|---:|---:|
| Button | `.btn` / `.btn.primary|secondary|danger|ghost|link` (+ kebab aliases) — no Button component | 387 | 256 | 131 | 66 | 60 |
| Input / TextBox | TextInput, PasswordInput (`components/ui/form`) | 98 | 96 | 2 | 31 | 2 |
| TextArea | TextareaInput (`components/ui/form`) | 19 | 19 | 0 | 13 | 0 |
| Select | SelectInput (`components/ui/form`) + domain EntitySelect wrappers | 57 | 55 | 2 | 21 | 1 |
| Checkbox / Radio | CheckboxField, RadioField (`components/ui/form`) | 46 | 46 | 0 | 17 | 0 |
| Form | FormGrid / FormField / FormSection / FormActions / FormModal | 241 | 241 | 0 | 25 | 0 |
| Modal / Dialog / Confirmation | Modal, ConfirmDialog, FormModal, Drawer (ADR-028) | 66 | 66 | 0 | 28 | 0 |
| DataTable / Table | UniversalDataTable -> WidthResponsiveDataTable (+ ServerDataTableFrame) | 50 | 47 | 3 | 33 | 1 |
| Pagination | PaginationBar + ServerDataTableFrame dual pagination | 14 | 14 | 0 | 9 | 0 |
| Filter / Toolbar | FilterPanel | 22 | 22 | 0 | 14 | 0 |
| Card | Card (`components/ui/Card`) | 51 | 51 | 0 | 18 | 0 |
| PageHeader | PageHeader / SectionHeader | 35 | 35 | 0 | 28 | 0 |
| Layout / Shell | AppLayout, AdminSystemLayout, DataIntegrationLayout, Breadcrumb, UserMenu | 8 | 8 | 0 | 4 | 0 |
| Alert / Toast / Banner | Banner (`components/ui/Banner`) — success/warning/error/info | 86 | 86 | 0 | 42 | 0 |
| Other shared UI | Tabs, Badge, TruncatedText, TechnicalDetails, EmptyState, LoadingState, DetailFields | 132 | 132 | 0 | 43 | 0 |

## Detaylar

### Button

- **Ortak altyapı:** `.btn` / `.btn.primary|secondary|danger|ghost|link` (+ kebab aliases) — no Button component
- **Not:** No Button.tsx — class-based `.btn` / `.btn-*` is the standard (ADR-032 §5).
- **Toplam / standart / dışı:** 387 / 256 / 131
- **Standart kullanan dosya sayısı:** 66
- **Standart dışı içeren dosya sayısı:** 60

**Standart dışı / karışık dosyalar:**
- `frontend/src/components/ActivityList.tsx`
- `frontend/src/components/AdapterSelect.tsx`
- `frontend/src/components/AssignCustomersToFairModal.tsx`
- `frontend/src/components/ContactList.tsx`
- `frontend/src/components/CustomerCommunicationFieldList.tsx`
- `frontend/src/components/CustomerList.tsx`
- `frontend/src/components/DeleteSelectedCustomersModal.tsx`
- `frontend/src/components/DuplicateGroupDetailView.tsx`
- `frontend/src/components/FairEntitySelect.tsx`
- `frontend/src/components/FairList.tsx`
- `frontend/src/components/Pagination.tsx`
- `frontend/src/components/ParticipationList.tsx`
- `frontend/src/components/customers/CustomerContactEnrichmentTab.tsx`
- `frontend/src/components/duplicateMerge/CopyableCustomerId.tsx`
- `frontend/src/components/duplicateMerge/MergeSummaryPanel.tsx`
- `frontend/src/components/fairs/FairBulkEmailBatchLogs.tsx`
- `frontend/src/components/fairs/FairBulkEmailWizard.tsx`
- `frontend/src/components/imports/MergeDiffViewer.tsx`
- `frontend/src/components/layout/AppLayout.tsx`
- `frontend/src/components/layout/NavLink.tsx`
- `frontend/src/components/layout/UserMenu.tsx`
- `frontend/src/components/mail_operations/MailOperationActionsMenu.tsx`
- `frontend/src/components/mail_templates/MailTemplateActionsMenu.tsx`
- `frontend/src/components/mail_templates/MailTemplatePreviewPanel.tsx`
- `frontend/src/components/mail_templates/MailTemplateTestEmailPanel.tsx`
- `frontend/src/components/scraper/AdapterFormModal.tsx`
- `frontend/src/components/scraper/AdapterLinkedFairsTab.tsx`
- `frontend/src/components/scraper/AdapterRunLogConsole.tsx`
- `frontend/src/components/scraper/EnrichmentRunLogExportMenu.tsx`
- `frontend/src/components/scraper/EnrichmentRunPanel.tsx`
- `frontend/src/components/scraper/EnrichmentStateResetPanel.tsx`
- `frontend/src/components/smtp/SmtpAccountForm.tsx`
- `frontend/src/components/todos/ManualTaskMailModal.tsx`
- `frontend/src/components/todos/TodoWorklistActivityModal.tsx`
- `frontend/src/components/ui/Breadcrumb.tsx`
- `frontend/src/components/ui/ConfirmDialog.tsx`
- `frontend/src/components/ui/DataTable.tsx`
- `frontend/src/components/ui/IconButton.tsx`
- `frontend/src/components/ui/PageHeader.tsx`
- `frontend/src/components/ui/TableEntityLink.tsx`
- `frontend/src/components/ui/Tabs.tsx`
- `frontend/src/components/ui/TechnicalDetails.tsx`
- `frontend/src/dev/TableStandardSmokePage.tsx`
- `frontend/src/pages/ActivitiesPage.tsx`
- `frontend/src/pages/AdapterManagementPage.tsx`
- `frontend/src/pages/CustomerDetailPage.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/DataIntegrationImportsPage.tsx`
- `frontend/src/pages/DataOperationAnalyzeResultPage.tsx`
- `frontend/src/pages/DataOperationDuplicateResultPage.tsx`
- `frontend/src/pages/DataOperationsPage.tsx`
- `frontend/src/pages/DatabaseBackupsPage.tsx`
- `frontend/src/pages/EnrichmentRunDetailPage.tsx`
- `frontend/src/pages/FairDetailPage.tsx`
- `frontend/src/pages/FollowUpsPage.tsx`
- `frontend/src/pages/ImportWizardPage.tsx`
- `frontend/src/pages/ScraperRunHistoryPage.tsx`
- `frontend/src/pages/SmtpAccountsPage.tsx`
- `frontend/src/pages/TodoDetailPage.tsx`
- `frontend/src/pages/TodosPage.tsx`

**Örnek standart dışı satırlar:**
- `frontend/src/components/ActivityList.tsx:109` —  — `<button`
- `frontend/src/components/AdapterSelect.tsx:113` —  — `<button`
- `frontend/src/components/AdapterSelect.tsx:125` —  — `<button`
- `frontend/src/components/AssignCustomersToFairModal.tsx:51` —  — `<button`
- `frontend/src/components/ContactList.tsx:79` —  — `<button`
- `frontend/src/components/CustomerCommunicationFieldList.tsx:78` —  — `<button`
- `frontend/src/components/CustomerList.tsx:193` —  — `<button`
- `frontend/src/components/CustomerList.tsx:207` —  — `<button`
- `frontend/src/components/customers/CustomerContactEnrichmentTab.tsx:201` —  — `<button`
- `frontend/src/components/customers/CustomerContactEnrichmentTab.tsx:209` —  — `<button`
- `frontend/src/components/DeleteSelectedCustomersModal.tsx:34` —  — `<button`
- `frontend/src/components/DuplicateGroupDetailView.tsx:574` —  — `<button`
- `frontend/src/components/DuplicateGroupDetailView.tsx:582` —  — `<button`
- `frontend/src/components/DuplicateGroupDetailView.tsx:633` —  — `<button`
- `frontend/src/components/DuplicateGroupDetailView.tsx:641` —  — `<button`

### Input / TextBox

- **Ortak altyapı:** TextInput, PasswordInput (`components/ui/form`)
- **Not:** Shared: TextInput / PasswordInput from ui/form.
- **Toplam / standart / dışı:** 98 / 96 / 2
- **Standart kullanan dosya sayısı:** 31
- **Standart dışı içeren dosya sayısı:** 2

**Standart dışı / karışık dosyalar:**
- `frontend/src/components/AdapterSelect.tsx`
- `frontend/src/components/FairEntitySelect.tsx`

**Örnek standart dışı satırlar:**
- `frontend/src/components/AdapterSelect.tsx:88` — raw:<input\b — `<input`
- `frontend/src/components/FairEntitySelect.tsx:165` — raw:<input\b — `<input`

### TextArea

- **Ortak altyapı:** TextareaInput (`components/ui/form`)
- **Not:** Shared: TextareaInput from ui/form.
- **Toplam / standart / dışı:** 19 / 19 / 0
- **Standart kullanan dosya sayısı:** 13
- **Standart dışı içeren dosya sayısı:** 0

### Select

- **Ortak altyapı:** SelectInput (`components/ui/form`) + domain EntitySelect wrappers
- **Not:** Shared: SelectInput from ui/form. Domain selects (FairEntitySelect, AdapterSelect) are OK wrappers.
- **Toplam / standart / dışı:** 57 / 55 / 2
- **Standart kullanan dosya sayısı:** 21
- **Standart dışı içeren dosya sayısı:** 1

**Standart dışı / karışık dosyalar:**
- `frontend/src/components/imports/ExcelMappingGrid.tsx`

**Örnek standart dışı satırlar:**
- `frontend/src/components/imports/ExcelMappingGrid.tsx:55` — raw:<select\b — `<select`
- `frontend/src/pages/ImportWizardPage.tsx:1123` — raw:<select\b — `<select`

### Checkbox / Radio

- **Ortak altyapı:** CheckboxField, RadioField (`components/ui/form`)
- **Not:** Shared: CheckboxField / RadioField only (ADR-032 §4).
- **Toplam / standart / dışı:** 46 / 46 / 0
- **Standart kullanan dosya sayısı:** 17
- **Standart dışı içeren dosya sayısı:** 0

### Form

- **Ortak altyapı:** FormGrid / FormField / FormSection / FormActions / FormModal
- **Not:** Shared form kit under components/ui/form (+ legacy FormField.tsx re-export).
- **Toplam / standart / dışı:** 241 / 241 / 0
- **Standart kullanan dosya sayısı:** 25
- **Standart dışı içeren dosya sayısı:** 0

### Modal / Dialog / Confirmation

- **Ortak altyapı:** Modal, ConfirmDialog, FormModal, Drawer (ADR-028)
- **Not:** ADR-028: Modal + ConfirmDialog (+ FormModal/Drawer).
- **Toplam / standart / dışı:** 66 / 66 / 0
- **Standart kullanan dosya sayısı:** 28
- **Standart dışı içeren dosya sayısı:** 0

### DataTable / Table

- **Ortak altyapı:** UniversalDataTable -> WidthResponsiveDataTable (+ ServerDataTableFrame)
- **Not:** ADR-032: UniversalDataTable → WidthResponsiveDataTable. DataTableShell scroll-only for specialty grids.
- **Toplam / standart / dışı:** 50 / 47 / 3
- **Standart kullanan dosya sayısı:** 33
- **Standart dışı içeren dosya sayısı:** 1

**Standart dışı / karışık dosyalar:**
- `frontend/src/components/imports/ExcelMappingGrid.tsx`

**Örnek standart dışı satırlar:**
- `frontend/src/components/imports/ExcelMappingGrid.tsx:43` — raw:<table\b — `<table className="data-table excel-mapping-grid">`
- `frontend/src/pages/ImportWizardPage.tsx:1008` — raw:<table\b — `<table className="data-table">`
- `frontend/src/pages/ImportWizardPage.tsx:1104` — raw:<table\b — `<table className="data-table mapping-table">`

### Pagination

- **Ortak altyapı:** PaginationBar + ServerDataTableFrame dual pagination
- **Not:** PaginationBar + ServerDataTableFrame dual pagination.
- **Toplam / standart / dışı:** 14 / 14 / 0
- **Standart kullanan dosya sayısı:** 9
- **Standart dışı içeren dosya sayısı:** 0

### Filter / Toolbar

- **Ortak altyapı:** FilterPanel
- **Not:** Shared: FilterPanel. Local `.filters` toolbars are non-standard if not FilterPanel.
- **Toplam / standart / dışı:** 22 / 22 / 0
- **Standart kullanan dosya sayısı:** 14
- **Standart dışı içeren dosya sayısı:** 0

### Card

- **Ortak altyapı:** Card (`components/ui/Card`)
- **Not:** Shared Card component only. Bare class token `card` on raw elements is a P1 violation.
- **Toplam / standart / dışı:** 51 / 51 / 0
- **Standart kullanan dosya sayısı:** 18
- **Standart dışı içeren dosya sayısı:** 0

### PageHeader

- **Ortak altyapı:** PageHeader / SectionHeader
- **Not:** PageHeader for pages; SectionHeader for nested sections.
- **Toplam / standart / dışı:** 35 / 35 / 0
- **Standart kullanan dosya sayısı:** 28
- **Standart dışı içeren dosya sayısı:** 0

### Layout / Shell

- **Ortak altyapı:** AppLayout, AdminSystemLayout, DataIntegrationLayout, Breadcrumb, UserMenu
- **Not:** App shell + nested Admin/DI layouts.
- **Toplam / standart / dışı:** 8 / 8 / 0
- **Standart kullanan dosya sayısı:** 4
- **Standart dışı içeren dosya sayısı:** 0

### Alert / Toast / Banner

- **Ortak altyapı:** Banner (`components/ui/Banner`) — success/warning/error/info
- **Not:** Shared Banner (success/warning/error/info). No parallel toast system. Field-level `.form-error` stays with FormField.
- **Toplam / standart / dışı:** 86 / 86 / 0
- **Standart kullanan dosya sayısı:** 42
- **Standart dışı içeren dosya sayısı:** 0

### Other shared UI

- **Ortak altyapı:** Tabs, Badge, TruncatedText, TechnicalDetails, EmptyState, LoadingState, DetailFields
- **Not:** Tabs, Badge, TruncatedText, TechnicalDetails, Empty/Loading states, Detail fields.
- **Toplam / standart / dışı:** 132 / 132 / 0
- **Standart kullanan dosya sayısı:** 43
- **Standart dışı içeren dosya sayısı:** 0

## Local modal wrappers (filename *Modal* without shared Modal import)

- `frontend/src/hooks/useModalForm.ts`

## Domain select wrappers

- `frontend/src/components/AdapterSelect.tsx`
- `frontend/src/components/FairEntitySelect.tsx`

## CSS override / hotspot map (`styles.css`)

- **table_layout_fixed**: 1 matches
- **min_width_forced_rem**: 14 matches
- **min_width_forced_px_large**: 8 matches
- **overflow_x_auto**: 2 matches
- **overflow_x_clip**: 2 matches
- **word_break_all**: 2 matches
- **page_local_table**: 21 matches
- **legacy_card_stack**: 17 matches
- **btn_aliases_ok**: 8 matches

### Sample CSS hits

**table_layout_fixed** (first 1):
- L6211: `table-layout: fixed;`

**min_width_forced_rem** (first 5):
- L119: `min-width: 2rem;`
- L368: `min-width: 12rem;`
- L1798: `min-width: 2rem;`
- L1865: `min-width: 11rem;`
- L2805: `min-width: 9rem;`

**min_width_forced_px_large** (first 5):
- L688: `min-width: 180px;`
- L1135: `@media (min-width: 768px) {`
- L1768: `min-width: 160px;`
- L1789: `min-width: 160px;`
- L2581: `min-width: 220px;`

**overflow_x_auto** (first 2):
- L530: `overflow-x: auto;`
- L6060: `overflow-x: auto;`

**overflow_x_clip** (first 2):
- L6234: `text-overflow: clip;`
- L6253: `text-overflow: clip;`

**word_break_all** (first 2):
- L4628: `word-break: break-all;`
- L5837: `word-break: break-all;`

**page_local_table** (first 5):
- L2770: `.excel-mapping-grid-wrap {`
- L2774: `.excel-mapping-grid-meta {`
- L2779: `.excel-mapping-grid-scroll {`
- L2786: `.excel-mapping-grid {`
- L2792: `.excel-mapping-grid th,`

**legacy_card_stack** (first 5):
- L1166: `.table-wrap.table-wrap--cards,`
- L1174: `.table-wrap.table-wrap--cards .data-table,`
- L1181: `.table-wrap.table-wrap--cards .data-table thead,`
- L1186: `.table-wrap.table-wrap--cards .data-table,`
- L1187: `.table-wrap.table-wrap--cards .data-table tbody,`

**btn_aliases_ok** (first 5):
- L5772: `.btn-primary {`
- L5783: `.btn-primary:hover:not(:disabled) {`
- L5787: `.btn-secondary {`
- L5798: `.btn-secondary:hover:not(:disabled) {`
- L5817: `.btn-primary:disabled,`

## Sorun haritası (öncelik)

0. **P0 gate** — PASS (0 violations).
1. **P1 gate** — PASS (0 violations).
2. **P2 gate** — PASS (0 violations).
3. **P3 gate** — PASS (0 violations).
4. **FINAL gate** — PASS (0 violations).
5. **Specialty** — Import Wizard mapping + ExcelMappingGrid scroll-only; merge UIs; entity selects.
6. **CSS** — leftover page-local table/overflow rules and `word-break: break-all` outside `.text-mono`.

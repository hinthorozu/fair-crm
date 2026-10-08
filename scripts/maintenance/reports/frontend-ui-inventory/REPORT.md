# FAIR CRM Frontend UI Inventory

Audit of `frontend/src` against PROJECT_CONSTITUTION, ADR-028/032/034, `docs/frontend/UI_DESIGN_SYSTEM.md`, and `docs/frontend/RESPONSIVE_UI_STANDARD.md`.

## P0 standardization gate

- **PASS:** YES
- **Total P0 violations:** 0
- Bare checkbox/radio (outside FormInputs): **0**
- Local `.filters` without FilterPanel: **0**
- Raw `<input|select|textarea>` (excl. specialty/domain allowlist): **0**
- Allowlist: `frontend/src/components/AdapterSelect.tsx`, `frontend/src/components/CustomerEntitySelect.tsx`, `frontend/src/components/FairEntitySelect.tsx`, `frontend/src/components/imports/ExcelMappingGrid.tsx`, `frontend/src/components/ui/form/FormInputs.tsx`

## P1 standardization gate

- **PASS:** YES
- **Total P1 violations:** 0
- Bare alert/toast class tokens (`banner`/`toast`/`import-toast`): **0**
- Bare `card` class token on raw elements: **0**

## P2 standardization gate

- **PASS:** YES
- **Total P2 violations:** 0
- Bare `form-error` class: **0**
- Legacy `link-button`: **0**
- Ad-hoc emptyState: **0**
- Ad-hoc page loading: **0**
- Bare table/list action wrappers: **0**

## P3 standardization gate

- **PASS:** YES
- **Total P3 violations:** 0
- Bare icon-button class tokens: **0**
- Pages missing PageShell: **0**
- Layouts missing NavLink: **0**

## Route auto-coverage

- **PASS:** YES
- AppRoute count: **47**
- Mounted page components: **61**
- Missing PageShell on mounted pages: **0**
- Unmounted page files: **0**
- Routes missing smoke catalog: **0**

## FINAL standardization gate

- **PASS:** YES
- **Total FINAL violations:** 0
- Bare `field-error`: **0**
- Bare `modal-actions`: **0**
- `form-actions` inside Modal/FormModal: **0**
- Legacy CSS breakpoints: **0**
- Icon buttons missing aria-label: **0**
- Route coverage violations: **0**
- Prior gates failed: **NO**
- Breakpoints found: 767, 768, 1023, 1024, 1440

## Shared catalog

- `components/ui`: Badge.tsx, Banner.tsx, Breadcrumb.tsx, Button.tsx, Card.tsx, ConfirmDialog.tsx, DataTable.tsx, DetailFields.tsx, Drawer.tsx, EmptyState.tsx, FieldError.tsx, FilterPanel.tsx, FormActions.tsx, FormDirty.tsx, FormField.tsx, FormField.tsx, FormGrid.tsx, FormInputs.tsx, FormModal.tsx, FormSection.tsx, IconButton.tsx, LoadingState.tsx, Modal.tsx, PageHeader.tsx, PageShell.tsx, ResponsiveDataTable.tsx, SectionHeader.tsx, ServerDataTableFrame.tsx, TableEntityLink.tsx, TableRowActions.tsx, Tabs.tsx, TechnicalDetails.tsx, TruncatedText.tsx, UniversalDataTable.tsx, UniversalDataTableSelection.tsx, WidthResponsiveDataTable.tsx
- Form kit: FieldError.tsx, FormActions.tsx, FormDirty.tsx, FormField.tsx, FormGrid.tsx, FormInputs.tsx, FormModal.tsx, FormSection.tsx

## Category summary

| UI türü | Ortak altyapı | Toplam hit | Standart | Standart dışı |
|---|---|---:|---:|---:|
| Button | `.btn` / `.btn.primary|secondary|danger|ghost|link` (+ kebab aliases) — no Button component | 523 | 351 | 172 |
| Input / TextBox | TextInput, PasswordInput (`components/ui/form`) | 206 | 203 | 3 |
| TextArea | TextareaInput (`components/ui/form`) | 27 | 27 | 0 |
| Select | SelectInput (`components/ui/form`) + domain EntitySelect wrappers | 101 | 99 | 2 |
| Checkbox / Radio | CheckboxField, RadioField (`components/ui/form`) | 91 | 91 | 0 |
| Form | FormGrid / FormField / FormSection / FormActions / FormModal | 473 | 473 | 0 |
| Modal / Dialog / Confirmation | Modal, ConfirmDialog, FormModal, Drawer (ADR-028) | 111 | 111 | 0 |
| DataTable / Table | UniversalDataTable -> WidthResponsiveDataTable (+ ServerDataTableFrame) | 80 | 75 | 5 |
| Pagination | PaginationBar + ServerDataTableFrame dual pagination | 14 | 14 | 0 |
| Filter / Toolbar | FilterPanel | 33 | 33 | 0 |
| Card | Card (`components/ui/Card`) | 86 | 86 | 0 |
| PageHeader | PageHeader / SectionHeader | 78 | 78 | 0 |
| Layout / Shell | AppLayout, AdminSystemLayout, DataIntegrationLayout, Breadcrumb, UserMenu | 7 | 7 | 0 |
| Alert / Toast / Banner | Banner (`components/ui/Banner`) — success/warning/error/info | 169 | 169 | 0 |
| Other shared UI | Tabs, Badge, TruncatedText, TechnicalDetails, EmptyState, LoadingState, DetailFields | 237 | 237 | 0 |

## Gate commands

```powershell
python scripts/maintenance/inventory_frontend_ui.py --gate P0
python scripts/maintenance/inventory_frontend_ui.py --gate P1
python scripts/maintenance/inventory_frontend_ui.py --gate P2
python scripts/maintenance/inventory_frontend_ui.py --gate P3
python scripts/maintenance/inventory_frontend_ui.py --gate FINAL
python scripts/maintenance/inventory_frontend_ui.py --gate ALL
```

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
- AppRoute count: **34**
- Mounted page components: **29**
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

## Gate commands

```powershell
python scripts/maintenance/inventory_frontend_ui.py --gate P0
python scripts/maintenance/inventory_frontend_ui.py --gate P1
python scripts/maintenance/inventory_frontend_ui.py --gate P2
python scripts/maintenance/inventory_frontend_ui.py --gate P3
python scripts/maintenance/inventory_frontend_ui.py --gate FINAL
python scripts/maintenance/inventory_frontend_ui.py --gate ALL
```

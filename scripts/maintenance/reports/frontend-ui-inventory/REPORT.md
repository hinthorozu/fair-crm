# FAIR CRM Frontend UI Inventory

Audit of `frontend/src` against PROJECT_CONSTITUTION, ADR-028/032/034, `docs/frontend/UI_DESIGN_SYSTEM.md`, and `docs/frontend/RESPONSIVE_UI_STANDARD.md`.

## P0 standardization gate

- **PASS:** NO
- **Total P0 violations:** 15
- Bare checkbox/radio (outside FormInputs): **2**
- Local `.filters` without FilterPanel: **1**
- Raw `<input|select|textarea>` (excl. specialty/domain allowlist): **12**
- Allowlist: `frontend/src/components/AdapterSelect.tsx`, `frontend/src/components/CustomerEntitySelect.tsx`, `frontend/src/components/FairEntitySelect.tsx`, `frontend/src/components/imports/ExcelMappingGrid.tsx`, `frontend/src/components/ui/form/FormInputs.tsx`

## P1 standardization gate

- **PASS:** NO
- **Total P1 violations:** 1
- Bare alert/toast class tokens (`banner`/`toast`/`import-toast`): **0**
- Bare `card` class token on raw elements: **1**

## P2 standardization gate

- **PASS:** NO
- **Total P2 violations:** 2
- Bare `form-error` class: **0**
- Legacy `link-button`: **0**
- Ad-hoc emptyState: **0**
- Ad-hoc page loading: **0**
- Bare table/list action wrappers: **2**

## P3 standardization gate

- **PASS:** NO
- **Total P3 violations:** 5
- Bare icon-button class tokens: **0**
- Pages missing PageShell: **5**
- Layouts missing NavLink: **0**

## Route auto-coverage

- **PASS:** NO
- AppRoute count: **42**
- Mounted page components: **35**
- Missing PageShell on mounted pages: **3**
- Unmounted page files: **6**
- Routes missing smoke catalog: **2**

## FINAL standardization gate

- **PASS:** NO
- **Total FINAL violations:** 26
- Bare `field-error`: **0**
- Bare `modal-actions`: **0**
- `form-actions` inside Modal/FormModal: **12**
- Legacy CSS breakpoints: **2**
- Icon buttons missing aria-label: **0**
- Route coverage violations: **11**
- Prior gates failed: **YES**
- Breakpoints found: 520, 767, 768, 800, 1023, 1024, 1440

## Gate commands

```powershell
python scripts/maintenance/inventory_frontend_ui.py --gate P0
python scripts/maintenance/inventory_frontend_ui.py --gate P1
python scripts/maintenance/inventory_frontend_ui.py --gate P2
python scripts/maintenance/inventory_frontend_ui.py --gate P3
python scripts/maintenance/inventory_frontend_ui.py --gate FINAL
python scripts/maintenance/inventory_frontend_ui.py --gate ALL
```

# SPECIALTY_COMPONENTS

Only raw inputs/selects/tables and specialty comboboxes. Bare `<button>` with `.btn` is **not** specialty.

Total true specialty consumers: **19**

| File:line | Kind | Why raw/specialty | Design tokens still used | Route evidence | Screenshot evidence | QA |
|---|---|---|---|---|---|---|
| `src/components/AdapterSelect.tsx:88` | raw_input | Combobox search/filter for adapters; custom listbox UX | .adapter-select + form-control height/border/radius/focus | /data-integration/scraper-test, /data-integration/enrichment | `data-integration_scraper-test__w1440.png` | NOT VERIFIED |
| `src/components/AssignCustomersToFairModal.tsx:66` | FairEntitySelect | Raw control without mapped evidence | unknown | NOT VERIFIED | `NOT VERIFIED` | NOT VERIFIED |
| `src/components/FairEntitySelect.tsx:165` | raw_input | Async fair combobox with search | entity-select control tokens | /data-integration/imports/new | `data-integration_imports_new__w1440.png` | NOT VERIFIED |
| `src/components/FairForm.tsx:264` | AdapterSelect | Raw control without mapped evidence | unknown | NOT VERIFIED | `NOT VERIFIED` | NOT VERIFIED |
| `src/components/imports/ExcelMappingGrid.tsx:55` | raw_select | Dense mapping grid cell editors need native select/table | global select chevron/border + table tokens | /data-integration/imports/continue/:batchId (mapping step — NOT captured; current batch is decisions) | `NOT VERIFIED (decisions-step screenshots only)` | NOT VERIFIED |
| `src/components/imports/ExcelMappingGrid.tsx:43` | raw_table | Dense mapping grid cell editors need native select/table | global select chevron/border + table tokens | /data-integration/imports/continue/:batchId (mapping step — NOT captured; current batch is decisions) | `NOT VERIFIED (decisions-step screenshots only)` | NOT VERIFIED |
| `src/components/scraper/EnrichmentRunPanel.tsx:187` | FairEntitySelect | Raw control without mapped evidence | unknown | NOT VERIFIED | `NOT VERIFIED` | NOT VERIFIED |
| `src/components/ui/DataTable.tsx:124` | raw_table | Raw control without mapped evidence | unknown | NOT VERIFIED | `NOT VERIFIED` | NOT VERIFIED |
| `src/components/ui/DataTable.tsx:174` | raw_table | Raw control without mapped evidence | unknown | NOT VERIFIED | `NOT VERIFIED` | NOT VERIFIED |
| `src/components/ui/form/FormInputs.tsx:29` | raw_input | Raw control without mapped evidence | unknown | NOT VERIFIED | `NOT VERIFIED` | NOT VERIFIED |
| `src/components/ui/form/FormInputs.tsx:198` | raw_input | Raw control without mapped evidence | unknown | NOT VERIFIED | `NOT VERIFIED` | NOT VERIFIED |
| `src/components/ui/form/FormInputs.tsx:264` | raw_input | Raw control without mapped evidence | unknown | NOT VERIFIED | `NOT VERIFIED` | NOT VERIFIED |
| `src/components/ui/form/FormInputs.tsx:135` | raw_textarea | Raw control without mapped evidence | unknown | NOT VERIFIED | `NOT VERIFIED` | NOT VERIFIED |
| `src/components/ui/form/FormInputs.tsx:114` | raw_select | Raw control without mapped evidence | unknown | NOT VERIFIED | `NOT VERIFIED` | NOT VERIFIED |
| `src/components/ui/WidthResponsiveDataTable.tsx:276` | raw_table | Raw control without mapped evidence | unknown | NOT VERIFIED | `NOT VERIFIED` | NOT VERIFIED |
| `src/pages/ImportWizardPage.tsx:1123` | raw_select | Wizard file/sheet/header raw controls | btn/form-control/card tokens | /data-integration/imports/new + continue | `data-integration_imports_new__w1440.png / continue_*` | NOT VERIFIED |
| `src/pages/ImportWizardPage.tsx:1008` | raw_table | Wizard file/sheet/header raw controls | btn/form-control/card tokens | /data-integration/imports/new + continue | `data-integration_imports_new__w1440.png / continue_*` | NOT VERIFIED |
| `src/pages/ImportWizardPage.tsx:1104` | raw_table | Wizard file/sheet/header raw controls | btn/form-control/card tokens | /data-integration/imports/new + continue | `data-integration_imports_new__w1440.png / continue_*` | NOT VERIFIED |
| `src/pages/ImportWizardPage.tsx:1036` | FairEntitySelect | Wizard file/sheet/header raw controls | btn/form-control/card tokens | /data-integration/imports/new + continue | `data-integration_imports_new__w1440.png / continue_*` | NOT VERIFIED |

## Summary

- PASS: 0
- FAIL: 0
- NOT VERIFIED: 19


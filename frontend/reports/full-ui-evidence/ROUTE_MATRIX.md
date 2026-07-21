# ROUTE_MATRIX

Base URL: `http://127.0.0.1:5175`
Login URL: `http://127.0.0.1:5176/login` (`VITE_DEV_BYPASS_ENABLED=false`)

Discovered IDs: `{"customer":"96715255-5b1b-5a4e-a8d6-1efa8e010da5","fair":"185f1197-beb6-4d98-a53f-1ed7e503ae14","todo":"14dbd7db-9a64-4608-81f5-a13bbae64945","adapter":"customer_contact_enrichment","runId":"ed0c1972-9936-4381-a512-cc67f1e2639b","batchId":"e302f4d8-5058-4753-afe6-186cf26e916f","dataOpRunId":"7c54a19a-2e30-4af3-ba93-e1d151f40a8d","dataOpKey":"analyze_customers_without_fair","adapters":[]}`

**Status rule:** PASS only after human visual QA of the screenshot. Metric-only capture (overflow/native checks) is **NOT VERIFIED**, not PASS.

Screenshot files exist for all listed routes × widths in `capture-results.json` (495 cells under `screenshots/`).

| Route | Test URL | 320 | 390 | 768 | 1024 | 1440 | 1920 | 2560 | 3440 | 3840 | Sonuç |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `/login` | `/login` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `/dashboard` | `/dashboard` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/customers` | `/customers` | PASS | PASS | NOT VERIFIED | NOT VERIFIED | PASS | PASS | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/customers/:id` | `/customers/96715255-5b1b-5a4e-a8d6-1efa8e010da5` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/fairs` | `/fairs` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/fairs/:id` | `/fairs/185f1197-beb6-4d98-a53f-1ed7e503ae14` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/fairs/:id/enrichment` | `/fairs/185f1197-beb6-4d98-a53f-1ed7e503ae14/enrichment` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/todos` | `/todos` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/todos/:id` | `/todos/14dbd7db-9a64-4608-81f5-a13bbae64945` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/follow-ups` | `/follow-ups` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/activities` | `/activities` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/data-integration/imports` | `/data-integration/imports` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/data-integration/imports/new` | `/data-integration/imports/new` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/data-integration/imports/fair/:fairId` | `/data-integration/imports/fair/185f1197-beb6-4d98-a53f-1ed7e503ae14` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/data-integration/jobs` | `/data-integration/jobs` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/data-integration/reports` | `/data-integration/reports` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/data-integration/adapters` | `/data-integration/adapters` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/data-integration/adapters/:adapterKey` | `/data-integration/adapters/customer_contact_enrichment` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/data-integration/run-history` | `/data-integration/run-history` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/data-integration/runs/:runId` | `/data-integration/runs/ed0c1972-9936-4381-a512-cc67f1e2639b?adapter_key=customer_contact_enrichment` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/data-integration/scraper-test` | `/data-integration/scraper-test` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/data-integration/enrichment` | `/data-integration/enrichment` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/admin/system/backups` | `/admin/system/backups` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/admin/smtp-operations/accounts` | `/admin/smtp-operations/accounts` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/admin/smtp-operations/templates` | `/admin/smtp-operations/templates` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/admin/smtp-operations/mail-operations` | `/admin/smtp-operations/mail-operations` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/admin/data-operations` | `/admin/data-operations` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/admin/data-operations/runs/:runId` | `/admin/data-operations/runs/7c54a19a-2e30-4af3-ba93-e1d151f40a8d?operation=analyze_customers_without_fair` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/imports` | `/imports` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/imports/fair/:fairId` | `/imports/fair/185f1197-beb6-4d98-a53f-1ed7e503ae14` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/dev/customers-responsive-pilot` | `/dev/customers-responsive-pilot` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/dev/table-standard-smoke` | `/dev/table-standard-smoke` | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| `/data-integration/imports/continue/:batchId` | `/data-integration/imports/continue/e302f4d8-5058-4753-afe6-186cf26e916f` | PASS | PASS | NOT VERIFIED | NOT VERIFIED | PASS | PASS | FAIL | FAIL | FAIL | FAIL |

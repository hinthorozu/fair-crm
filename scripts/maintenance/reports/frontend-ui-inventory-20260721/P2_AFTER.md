# P2 UI Standardization — After Report

Date: 2026-07-21

## Gate

| Metrik | Önce | Sonra |
|--------|-----:|------:|
| Bare `form-error` (page/field ad-hoc) | ~18+ | **0** |
| Legacy `link-button` | ~9 | **0** |
| Ad-hoc list empty (`text-muted` emptyState) | ~3 | **0** |
| Ad-hoc page loading (`Yükleniyor…` paragraph) | ~4+ | **0** |
| Bare table/list action wrappers | ~10+ | **0** |
| Broken EmptyState `message` without title | 2 | **0** (alias + title fix) |
| **P2 total violations** | — | **0 — PASS** |

## New shared primitives

- `FieldError` — standalone field/modal validation errors
- `TableEntityLink` — in-table entity navigation (replaces `link-button`)
- `TableRowActions` — Actions column wrapper
- `EmptyState.message` alias for `title`

## Intentional exceptions

- LoginPage `login-form-error` — auth chrome
- FairEntitySelect / AdapterSelect inline loading — domain combobox UX
- Import complete / restore polling specialty layouts (P1)
- TechnicalDetails unused — optional; TruncatedText covers technical columns
- Kebab action menus (mail) — dense domain menus, not link-action rows

## Verification

- Inventory: P0 PASS, P1 PASS, P2 PASS
- `npm run build` OK
- WidthResponsiveDataTable tests 5/5 OK
- Prior datatable responsive smoke: 14/14 PASS (re-run when Vite is up)

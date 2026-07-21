# P1 UI Standardization — After Report

Date: 2026-07-21

## Gate

| Metric | Before (inventory) | After |
|--------|-------------------|-------|
| Bare `.banner` / ad-hoc toast consumers | ~35+ files (raw `.banner` + `import-toast`) | **0** bare tokens |
| Shared Banner API | None | `components/ui/Banner.tsx` |
| Bare class token `card` on raw elements | **8 files** (~20+ hits) | **0** |
| Shared Card consumers | Partial | All former bare-`card` sites |
| **P1 total violations** | N/A (pre-gate) | **0 — PASS** |

## Intentional exceptions (not P1 violations)

| Location | Reason |
|----------|--------|
| `ImportWizardPage` `import-complete-banner` | Completion **layout** block inside Card (not a toast/alert) |
| `DatabaseBackupsPage` `restore-job-polling-banner` | Live job-tracking **panel** (status list), not notification Banner |
## Out of P1 scope (reported, not gated)

- Field/modal `.form-error` / `text-danger` for inline validation (FormField / confirm text) — not page toast API
- Compound names like `login-card`, `fair-info-card`, `backup-format-card` without bare `card` token

## Verification

- `python scripts/maintenance/inventory_frontend_ui.py` → P0 PASS, P1 PASS
- `npm run build` → success
- `WidthResponsiveDataTable` tests → 5/5 OK

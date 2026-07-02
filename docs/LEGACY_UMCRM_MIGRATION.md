# Legacy UMCRM Migration (Development)

This document describes how to migrate cleaned legacy UMCRM canonical JSON exports into the **Fair CRM development database**.

> **Development only.** Do not run these scripts against production.

## Prerequisites

1. PostgreSQL dev database configured in `backend/.env`
2. `APP_ENV=development` (or `local` / `test`)
3. Canonical legacy pipeline completed:
   - `scripts/legacy/cleaned/*.json`
   - `scripts/legacy/merge_plan/*.json`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/legacy/reset_fair_crm_dev_domain.py` | Clears Fair CRM domain tables for dev org (transactional) |
| `scripts/legacy/migrate_umcrm_to_kyrox.py` | Dry-run or apply migration |

## Domain reset (required before first apply)

Clears (dev organization only):

- `crm_activities`, `crm_customer_fair_participations`, `crm_contacts`
- `crm_import_rows`, `crm_import_batches`
- `crm_customers`, `crm_fairs`

Does **not** clear: Alembic history, users, roles, organizations, KYROX Core tables.

```bash
python scripts/legacy/reset_fair_crm_dev_domain.py
```

## Migration workflow

### 1. Dry-run

```bash
python scripts/legacy/migrate_umcrm_to_kyrox.py --dry-run
```

Reports:

- `scripts/legacy/migration_reports/umcrm_migration_dry_run.md`
- `scripts/legacy/migration_reports/umcrm_migration_dry_run.json`

### 2. Apply

`--apply` automatically runs domain reset unless `--skip-domain-reset` is passed.

```bash
python scripts/legacy/migrate_umcrm_to_kyrox.py --apply
```

Optional:

```bash
python scripts/legacy/migrate_umcrm_to_kyrox.py --apply --limit 100
python scripts/legacy/migrate_umcrm_to_kyrox.py --apply --skip-domain-reset
```

Apply reports:

- `scripts/legacy/migration_reports/umcrm_legacy_to_kyrox_fair_mapping.json`
- `scripts/legacy/migration_reports/umcrm_legacy_to_kyrox_customer_mapping.json`
- `scripts/legacy/migration_reports/umcrm_legacy_to_kyrox_participation_mapping.json`
- `scripts/legacy/migration_reports/umcrm_migration_apply_report.md`
- `scripts/legacy/migration_reports/umcrm_migration_apply_report.json`

## Mapping rules

| Legacy merge action | KYROX Customer |
|---------------------|----------------|
| `keep` | One customer per legacy ID |
| `merge` (auto) | One customer per merge group (canonical) |
| `manual_review` | Separate customer, flagged in description/activity |
| `risk` | Separate customer, flagged in description/activity |

- Emails: canonical `;` format (truncated to 255 chars; overflow in description)
- Participations: all legacy relations imported; duplicates skipped after merge resolution
- Activities: one migration note per customer (`source=import`)
- Contacts: not created (UMCRM dump has no contact table)
- Idempotency: deterministic UUID5 + mapping files; re-apply skips existing rows

## Verification

```bash
# Backend tests
cd backend && python -m pytest -q

# API (dev bypass + org header)
curl -H "Authorization: Bearer dev-bypass" \
     -H "X-Organization-Id: 00000000-0000-4000-8000-000000000010" \
     "http://127.0.0.1:8001/api/v1/customers?page=1&page_size=1"
```

Expected counts after full UMCRM import (approx.):

- Fairs: **115**
- Customers: **28,155**
- Participations: **29,561**
- Activities: **28,155**

## Related docs

- [IMPORT_ENGINE.md](IMPORT_ENGINE.md) — Excel wizard import (separate from legacy migration)
- Legacy analysis: `scripts/legacy/reports/`
- Legacy cleaning: `scripts/legacy/cleaned/`
- Merge plan: `scripts/legacy/merge_plan/`

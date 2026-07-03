# Infrastructure & Performance Roadmap

**Status:** Active — infrastructure planning only  
**Scope:** FAIR CRM backend, database, and operational performance. No product feature changes unless explicitly noted in a future item.

This document tracks technical work to keep the CRM responsive as data volume and background workloads grow. Each priority is self-contained: goal, affected paths, tasks, acceptance criteria, and references.

---

## Priority 1 — Database Index Strategy

### Goal

Design and apply proper database indexes before the CRM grows further.

Indexes must match real query patterns for list, search, duplicate analysis, import, and scraper handoff — not speculative coverage on every column.

### Scope

| Area | Why it matters |
|------|----------------|
| Customer list performance | Default sort and pagination on `crm_customers` (org-scoped, status filters, name sort) |
| Duplicate analysis performance | Full-table or large scans grouped by normalized name, email, phone, website |
| Import performance | Matching existing customers during preview and apply |
| Scraper import performance | Same matching paths as manual import, often at higher row volume |
| Search / filter / sort performance | API list queries, admin filters, and any `ORDER BY` on display or normalized names |

### Current baseline (pre-index, ~28k customers)

Captured with `backend/scripts/diagnose_crm_performance.py` against PostgreSQL when no duplicate-analysis job is blocking the event loop:

| Metric | Typical time |
|--------|----------------|
| List use case (DB layer) | ~126–239 ms |
| COUNT (org + non-deleted) | ~11–22 ms (sequential scan) |
| Sort + page (display name) | ~61–109 ms (sequential scan + sort) |
| `load_list_summaries(25)` | ~12–16 ms |

`EXPLAIN` on name-sorted list queries showed a missing index on `(organization_id, lower(display_name))`, causing sequential scans on sort paths.

**Note:** Background duplicate analysis on the full customer set previously blocked the API for minutes when run on the main event loop. That was addressed with thread-pool background jobs; index work remains separate and still required for sustainable list and analysis performance.

### Tasks

- [ ] **Review all critical tables and queries** — `crm_customers`, communication child tables (`crm_customer_emails`, `crm_customer_phones`, `crm_customer_websites`), import/scraper-related tables, and data-operation query paths. Use `EXPLAIN (ANALYZE, BUFFERS)` on production-like volume.
- [ ] **Identify missing indexes** — Document each slow query, current plan (seq scan vs index scan), and proposed index DDL.
- [ ] **Add indexes for high-traffic access patterns**, including at minimum:
  - `organization_id` (org-scoped filters on all tenant tables)
  - `status` (active / archived / deleted filters)
  - `deleted_at` (soft-delete and cleanup queries)
  - `normalized_name` (duplicate grouping by company name)
  - `display_name` sorting — functional index on `lower(display_name)` with partial predicate excluding deleted rows where appropriate
  - **Communication fields** — phone and website value lookups for duplicate and import matching (email indexes deferred until normalization rules and Phase 2 review are finalized; see [CUSTOMER_COMMUNICATION_PERFORMANCE.md](CUSTOMER_COMMUNICATION_PERFORMANCE.md))
- [ ] **Apply migration `0023` or equivalent manual SQL** if Alembic upgrade is blocked in an environment.
- [ ] **Benchmark before and after** — Re-run `diagnose_crm_performance.py` and capture list COUNT, sort+page, duplicate-analysis-adjacent lookups, and import match queries. Record results in this section.
- [ ] **Make index review mandatory** for every new table and major query (see process below).

### Migration `0023` — CRM list and duplicate-analysis indexes

Alembic revision: `backend/alembic/versions/0023_crm_list_performance_indexes.py`  
Revises: `0022_duplicate_group_merge_audit_logs`

**Apply via Alembic (preferred):**

```bash
cd fair-crm/backend
alembic upgrade head
```

**Equivalent manual SQL (PostgreSQL):**

```sql
CREATE INDEX IF NOT EXISTS ix_crm_customers_org_status
  ON crm_customers (organization_id, status);

CREATE INDEX IF NOT EXISTS ix_crm_customers_org_normalized_name
  ON crm_customers (organization_id, normalized_name);

CREATE INDEX IF NOT EXISTS ix_crm_customers_deleted_at
  ON crm_customers (deleted_at);

CREATE INDEX IF NOT EXISTS ix_crm_customers_org_display_name_lower
  ON crm_customers (organization_id, lower(display_name))
  WHERE status <> 'deleted';

CREATE INDEX IF NOT EXISTS ix_crm_customer_phones_phone
  ON crm_customer_phones (phone);

CREATE INDEX IF NOT EXISTS ix_crm_customer_websites_website
  ON crm_customer_websites (website);
```

After manual apply, stamp Alembic if needed: `alembic stamp 0023_crm_list_performance_indexes`.

### Acceptance criteria

- Migration `0023` applied (or manual SQL + Alembic stamp) in dev, staging, and production.
- `diagnose_crm_performance.py` post-index run shows measurable improvement on sort+page and org-scoped filters, with `EXPLAIN` confirming index use where expected.
- No new indexes added without a mapped slow query or documented access pattern.
- Index review checklist completed for any schema or query change merged after this item.

### Mandatory index review process

For **every new table** and **every major query change** (new list endpoint, new grouping field, new import match rule):

1. List expected `WHERE`, `JOIN`, `ORDER BY`, and `GROUP BY` clauses.
2. Run `EXPLAIN ANALYZE` on staging with realistic row counts.
3. If sequential scan on a growing table (>10k rows or expected to exceed that), propose an index in the same PR or a linked migration.
4. Document partial-index rationale when filtering on `status <> 'deleted'` or similar subsets.
5. Avoid redundant indexes that duplicate composite leading columns without measured benefit.

### After-index benchmark (fill in when complete)

| Metric | Before | After | Notes |
|--------|--------|-------|-------|
| List use case (DB) | ~126–239 ms | _TBD_ | |
| COUNT (org + non-deleted) | ~11–22 ms | _TBD_ | |
| Sort + page (display name) | ~61–109 ms | _TBD_ | Target: index scan on `ix_crm_customers_org_display_name_lower` |
| Duplicate phone/website lookup | _TBD_ | _TBD_ | |
| Import match sample query | _TBD_ | _TBD_ | |

### References

- Diagnose script: `backend/scripts/diagnose_crm_performance.py`
- Customer list repository: `backend/app/modules/customers/infrastructure/repositories/customer_repository.py`
- Communication batch loading: `backend/app/modules/customers/infrastructure/repositories/customer_communication_repository.py`
- Duplicate / data-operation paths: [CUSTOMER_CLEANUP_ARCHITECTURE.md](CUSTOMER_CLEANUP_ARCHITECTURE.md)
- Communication index deferral (Phase 2): [CUSTOMER_COMMUNICATION_PERFORMANCE.md](CUSTOMER_COMMUNICATION_PERFORMANCE.md)
- Import matching rules: [import/MATCHING_RULES.md](import/MATCHING_RULES.md)
- Request / SQL observability: `backend/app/core/request_timing.py`, `backend/app/core/performance_monitoring.py`

---

## Future priorities (placeholder)

Additional infrastructure and performance items (connection pool tuning, background job isolation, frontend list refresh patterns, import bulk paths) will be added here as separate numbered priorities. This document does not change product behavior until each item is executed and tracked independently.

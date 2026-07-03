# Customer Communication — Phase 2 Performance Review (TODO)

**Status:** Deferred — documentation only  
**Date:** 2026-07-03  
**Related:** Migration `0020_customer_communications`, [DECISIONS.md](DECISIONS.md) (ADR-031)

---

## Context

Customer phone, email, and website data now lives in child tables:

| Table | Purpose |
|-------|---------|
| `crm_customer_phones` | One row per phone number |
| `crm_customer_emails` | One row per email address |
| `crm_customer_websites` | One row per website |

Scalar columns on `crm_customers` (`phone`, `email`, `website`) remain for backward compatibility and are kept in sync on write.

**Current decision:** No additional indexes on communication values are added in Phase 1. The dataset is still small, and import / duplicate / merge business rules are still evolving. Index strategy should be decided after real query patterns are stable.

**Explicit non-goals for now:**

- No migration
- No new indexes
- No database schema changes
- No application code changes for performance

---

## Phase 2 Performance Review

Revisit when **any** trigger below is met:

| Trigger | Threshold |
|---------|-----------|
| Customer count | > 100,000 |
| Import batch size | > 50,000 rows |
| Duplicate analysis | Becomes slow in production or staging |
| Merge operation | Becomes slow in production or staging |

---

## Future review items

When triggered, run a structured performance review:

### 1. Measure before indexing

Run `EXPLAIN ANALYZE` on the heaviest paths:

- **Import lookup queries** — matching existing customers by phone, email, or website during import preview/apply
- **Duplicate grouping queries** — admin data-operation duplicate analysis (group by email, phone, domain, etc.)
- **Merge lookup queries** — loading and reconciling communication rows when merging winner/loser customers

Capture baseline latency, row counts, and sequential scan hotspots.

### 2. Index candidates (decide after EXPLAIN)

Consider indexes on **normalized** communication values (exact columns TBD after normalization rules stabilize):

| Candidate | Columns (illustrative) |
|-----------|-------------------------|
| Email lookup | `organization_id` + normalized email |
| Phone lookup | `organization_id` + normalized phone |
| Domain lookup | `organization_id` + normalized domain |

Additional options if profiling warrants:

- **Partial indexes** — e.g. `is_primary = true` only, or active-customer subsets
- **Composite indexes** aligned to actual `WHERE` / `GROUP BY` clauses from duplicate and import jobs

Do not add indexes speculatively; each index must map to a measured slow query.

### 3. Bulk operations

Review bulk import and upsert paths:

- Batch insert/update for communication child rows during large imports
- Avoid per-row round trips where merge or import applies thousands of communication changes
- Consider `COPY` / bulk upsert patterns for maintenance-scale backfills

---

## Checklist (when Phase 2 starts)

- [ ] Confirm trigger threshold met (document which one)
- [ ] `EXPLAIN ANALYZE` — import lookup queries
- [ ] `EXPLAIN ANALYZE` — duplicate grouping queries
- [ ] `EXPLAIN ANALYZE` — merge lookup queries
- [ ] Propose index DDL with measured benefit (new migration only after approval)
- [ ] Re-run duplicate/import/merge benchmarks on staging with production-like volume
- [ ] Update this document with findings and accepted index strategy

---

## References

- Child table migration: `backend/alembic/versions/0020_customer_communications.py`
- List API batch loading: `SqlAlchemyCustomerCommunicationRepository.load_list_summaries()`
- Duplicate analysis: `docs/CUSTOMER_CLEANUP_ARCHITECTURE.md` (internal merge/cleanup)
- Import matching: `docs/import/MATCHING_RULES.md`

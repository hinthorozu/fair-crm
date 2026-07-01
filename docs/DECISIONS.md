# Architecture Decisions

## ADR-001 — Use `fair-crm` as the product repository name

Status: Accepted

The previous repository name `fuar-crm` is Turkish. The new product repository uses `fair-crm` to align with backend, API, database, and domain naming standards.

Frontend labels and user-facing messages remain Turkish.

## ADR-002 — Use KYROX Core for platform capabilities

Status: Accepted

FAIR CRM must not reimplement authentication, authorization, organization, membership, audit, settings, background jobs, or notifications.

Those concerns belong to KYROX Core.

## ADR-003 — Customer is the first aggregate, not Company

Status: Accepted

The first CRM aggregate is `Customer` rather than `Company`.

Reason:

FAIR CRM must support exhibitors, leads, suppliers, sponsors, organizers, partners, and other CRM account types. `Company` is too narrow and may cause future model drift.

Company/legal information will be represented as fields within the Customer aggregate.

## ADR-004 — Old `fuar-crm` remains reference-only

Status: Accepted

The old `fuar-crm` repository can be used as a reference for workflows, fields, and existing business assumptions.

It should not be used as the target architecture.

## ADR-005 — Import must use preview and merge decision workflow

Status: Accepted

Imported data must not be blindly inserted.

The product must support:

- Import preview
- Duplicate detection
- Possible match suggestions
- Merge/update decisions
- Row-level validation

## ADR-006 — Backend/API/database naming is English, frontend user-facing text is Turkish

Status: Accepted

This convention is inherited from KYROX project standards.

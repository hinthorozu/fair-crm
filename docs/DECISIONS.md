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

## ADR-007 — KYROX Core as independent platform service

Status: Accepted (revised)

KYROX Core **v0.4.0** is an **independent reusable backend platform service**. FAIR CRM is an **independent product service**. They run as **separate deployments**.

Rules:

- Integrate with Core through **public HTTP APIs** (and later SDK/events when available).
- Do **not** import kyrox-core Python modules (`app.modules.*`, `app.db.*`, etc.).
- Do **not** share SQLAlchemy Session or database with Core.
- Do **not** mount Core routers inside the Fair CRM application.
- Do **not** create cross-repository database foreign keys.

Rationale:

- Core is a platform service consumed by products through documented contracts.
- Clear deployment, versioning, and ownership boundaries between platform and product.
- Aligns with kyrox-core Backend Architecture Standards: products integrate via public API.

Local JWT validation using the same `JWT_SECRET_KEY` configuration is permitted — this is config alignment, not a Core code import.

See [INTEGRATION_WITH_CORE.md](INTEGRATION_WITH_CORE.md).

## ADR-008 — Fair CRM as separate FastAPI service (internal modular monolith)

Status: Accepted (revised)

FAIR CRM runs as its **own FastAPI service**, separate from KYROX Core. Internally it is a **modular monolith**: one product codebase, one process, layered modules under `backend/app/modules/`.

Rules:

- Fair CRM and Core have **different base URLs**, **different databases**, and **independent deploy units**.
- Product modules follow layered architecture (domain → application → infrastructure → api), aligned with kyrox-core conventions.
- Core platform routes (auth, orgs, audit query, settings, jobs, notifications) are **not** served by Fair CRM — clients call Core directly.
- Extraction of Fair CRM internal modules into separate services is allowed later if required — Core remains a separate platform service regardless.

See [ARCHITECTURE.md](ARCHITECTURE.md).

## ADR-009 — Evaluate platform reusability before every new feature

Status: Accepted

Before implementing any new Fair CRM business feature, evaluate whether the capability is **generic platform infrastructure** reusable across KYROX products.

Rules:

1. **Evaluate first** — During Phase 1 design (before Phase 2 code), ask: could another product (not only Fair CRM) need this without CRM-specific semantics?
2. **If platform-generic** — Stop Fair CRM implementation. Document the need and **propose it for KYROX Core** first. Wait for approval and Core delivery (or an explicit decision to defer) before continuing in fair-crm.
3. **If product-specific** — Proceed in fair-crm. CRM domain logic, fair/exhibitor workflows, and Fair CRM permission semantics stay here.
4. **Integrate via Core APIs** — When Core already provides the capability, consume it through public APIs; do not reimplement or duplicate in fair-crm.

Examples:

| Capability | Owner |
|------------|-------|
| Auth, RBAC, audit write, settings, jobs, notifications | KYROX Core |
| Customer, import pipeline, duplicate merge, fair participation | Fair CRM |
| New generic permission-check pattern, file storage, webhooks | Evaluate → likely Core |

Report platform needs in design docs (see [ARCHITECTURE.md](ARCHITECTURE.md) §13) and track in kyrox-platform before changing kyrox-core.

## ADR-010 — Hall / Stand on CustomerFairParticipation, not Customer or Fair

Status: Accepted (Sprint 06)

Fair-specific exhibitor data (hall, stand, fair-specific notes) belongs on the **CustomerFairParticipation** join entity, not on Customer or Fair aggregates. Import engine will resolve/create participations and write hall/stand there.

## ADR-011 — Future Activity ↔ Participation link (deferred)

Status: Proposed — not implemented in Sprint 06

Activities may later reference an optional `participation_id` to tie timeline entries to a specific fair visit/exhibitor context. No schema change in Sprint 06; add when activity UX requires fair-scoped filtering.

## ADR-012 — Fair Context Required for Imports

Status: Accepted (Sprint 07 Smart Import Wizard design)

**Decision:**

Smart Import batches must be associated with a selected Fair. The import source will not provide or resolve `fair_name`.

**Rationale:**

In real workflows, exhibitor lists are collected for a known fair. Requiring Fair context prevents incorrect fair matching and ensures hall/stand data is stored on CustomerFairParticipation.

**Consequences:**

- Import Wizard requires Fair selection (Screen 3).
- `fair_name` is not a supported mapping field.
- Duplicate detection must evaluate both Customer and CustomerFairParticipation.
- Hall/Stand belong to participation records, not Customer or Fair.
- Import batch persists `fair_id` for the entire batch.
- Alternative entry from Fair Detail pre-fills Fair context.

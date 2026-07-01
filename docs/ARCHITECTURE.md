# FAIR CRM Architecture

**Status:** Sprint 1.0.0 Phase 2 — Implementation  
**Platform dependency:** kyrox-core **v0.4.0** (independent platform service)  
**Related:** [INTEGRATION_WITH_CORE.md](INTEGRATION_WITH_CORE.md), [CUSTOMER_DESIGN.md](CUSTOMER_DESIGN.md), [DECISIONS.md](DECISIONS.md)

---

## 1. Purpose

This document defines the target architecture for **FAIR CRM** — the first product on the KYROX platform baseline.

FAIR CRM is an **independent product service**: its own FastAPI application, its own deployment, and its own product database. **KYROX Core** is a separate, independently deployed **platform service**. The two communicate **only through Core public APIs** (and later SDK/events if needed).

FAIR CRM is organized internally as a **modular monolith** — one codebase, one process, layered modules — but it is **not** the same service as kyrox-core.

Layering follows [kyrox-core Backend Architecture Standards](../../kyrox-core/docs/BACKEND_ARCHITECTURE_STANDARDS.md) as a **convention reference**, not as an import dependency.

---

## 2. Architectural decisions (summary)

| Decision | Choice | ADR |
|----------|--------|-----|
| Core relationship | Independent platform **service**; public API integration | ADR-007 |
| Product deployment | Independent FastAPI **service** (modular monolith internally) | ADR-008 |
| Core imports | **Forbidden** — no `from app.modules...` from kyrox-core | ADR-007 |
| Database | **Separate** product database; no shared SQLAlchemy session with Core | ADR-007 |
| Cross-repo DB coupling | **Forbidden** — no shared DB, no FKs to Core tables | ADR-007 |
| Tenancy | `organization_id` (UUID) from Core; logical reference only | ADR-002 |
| Language | English backend/API/DB; Turkish frontend labels | ADR-006 |

---

## 3. System context

```text
┌─────────────────────┐         HTTP (public APIs)        ┌─────────────────────┐
│   Client / Frontend │ ────────────────────────────────► │    KYROX Core       │
│                     │   /api/v1/auth/login, orgs, ...   │  (platform service) │
└─────────┬───────────┘                                   │  port e.g. 8000     │
          │                                               └──────────┬──────────┘
          │  HTTP  /api/v1/customers, ...                            │
          │                                                          │ Core DB
          ▼                                               ┌──────────▼──────────┐
┌─────────────────────┐         HTTP (public APIs)        │    PostgreSQL       │
│     FAIR CRM        │ ─────────────────────────────────►│   (kyrox_core)      │
│  (product service)  │   audit, settings, jobs, notif.   └─────────────────────┘
│  port e.g. 8001     │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│    PostgreSQL       │
│    (fair_crm)       │
│  crm_customers, ... │
└─────────────────────┘
```

**Two services, two databases, one auth token.**

Clients typically authenticate via **Core** (`POST /api/v1/auth/login`), then call **Fair CRM** with the same JWT and `X-Organization-Id`. Fair CRM validates the token and checks permissions through Core APIs (see [INTEGRATION_WITH_CORE.md](INTEGRATION_WITH_CORE.md) for gaps).

---

## 4. Repository layout

```text
fair-crm/
├── backend/
│   ├── app/
│   │   ├── main.py                 # Fair CRM FastAPI app — product routes only
│   │   ├── core/
│   │   │   ├── config.py           # FAIR_CRM_* settings; KYROX_CORE_BASE_URL
│   │   │   ├── logging.py
│   │   │   └── exceptions.py
│   │   ├── db/
│   │   │   └── session.py          # Product DB session only
│   │   ├── integrations/
│   │   │   └── kyrox_core/         # HTTP client adapters to Core public APIs
│   │   │       ├── client.py
│   │   │       ├── auth.py         # JWT validation (shared secret config)
│   │   │       ├── audit.py
│   │   │       ├── settings.py
│   │   │       ├── jobs.py
│   │   │       └── notifications.py
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── router.py       # Product routes only
│   │   └── modules/                # Product bounded contexts
│   │       └── customers/
│   │           ├── domain/
│   │           ├── application/
│   │           ├── infrastructure/
│   │           └── api/
│   ├── alembic/                    # Product schema only (crm_* tables)
│   └── tests/
├── docs/
├── scripts/
│   └── quality_check.py
├── alembic.ini
├── requirements.txt                # No kyrox-core package dependency
└── .env.example
```

**Rules:**

- Product code lives only under `fair-crm/backend/app/modules/`.
- **Do not** import kyrox-core Python modules (`app.modules.*`, `app.db.*`, etc.).
- **Do not** mount Core routers inside the Fair CRM app.
- **Do not** share `DATABASE_URL` with Core.
- Platform access goes through `app/integrations/kyrox_core/` HTTP adapters only.

---

## 5. Layered architecture (per product module)

Each product module uses four layers (convention aligned with kyrox-core):

| Layer | Responsibility | Example (`customers`) |
|-------|----------------|------------------------|
| **domain** | Entities, value objects, ports | `Customer`, `CustomerRepository` |
| **application** | Use cases | `CreateCustomerUseCase` |
| **infrastructure** | SQLAlchemy, product DB repos | `SqlAlchemyCustomerRepository` |
| **api** | FastAPI routes, schemas, DI | `POST /api/v1/customers` |

### Dependency direction (inward)

```text
api → application → domain
infrastructure → domain (implements ports)
integrations/kyrox_core → used by application or api (via ports)
```

Product **domain** must not import HTTP clients or Core response types. Core integration is behind **ports** implemented in `integrations/kyrox_core/`.

---

## 6. Product module boundaries

| Module | Sprint | Scope |
|--------|--------|-------|
| **customers** | 1.0.0 | CRM account aggregate; org-scoped CRUD |
| **contacts** | 1.1.0 | People linked to customers |
| **fairs** | 1.2.0 | Fair events |
| **participations** | 1.3.0 | Customer ↔ fair participation |
| **import** | 1.4.0 | Import pipeline, duplicate detection |
| **scraper** | 1.5.0 | Scraper integration |
| **reporting** | deferred | Reports and export |

**Cross-module rules:**

- Modules communicate via application services — not cross-infrastructure imports.
- Shared product primitives (if needed) go under `backend/app/shared/`.
- Each module owns `crm_*` tables in the **fair_crm** database.

---

## 7. Database strategy

### Separate databases — no cross-repository coupling

| Service | Database | Tables | Migrations |
|---------|----------|--------|------------|
| **kyrox-core** | `kyrox_core` (example) | `identity_*`, `audit_logs`, `platform_*` | Core Alembic through `20260701_0024` |
| **fair-crm** | `fair_crm` (example) | `crm_customers`, … | Product Alembic in fair-crm repo |

**Connection:** Fair CRM uses its own `DATABASE_URL` and SQLAlchemy `Session`. Core uses its own — **no shared session, no shared connection pool.**

**Organization reference:** Product tables store `organization_id` (UUID) issued by Core. This is a **logical tenant key**, not a foreign key to `identity_organizations`. Fair CRM validates that the caller's org context is authorized via Core APIs before trusting the value.

**Naming:** Product tables use the `crm_` prefix.

---

## 8. API surface

### Fair CRM service (product only)

Base URL: e.g. `http://localhost:8001/api/v1`

| Route group | Examples |
|-------------|----------|
| Health | `GET /health` |
| Customers | `POST /customers`, `GET /customers`, … |

Fair CRM **does not** expose Core platform routes. Auth, org management, and platform services are on the **Core base URL** (e.g. `http://localhost:8000/api/v1`).

### KYROX Core service (platform)

Documented in [kyrox-core README](../../kyrox-core/README.md). Clients and Fair CRM integration layer call Core directly for platform operations.

---

## 9. Request pipeline (Fair CRM)

```text
HTTP Request → Fair CRM
  → JWT validation (local decode using configured JWT secret — see INTEGRATION_WITH_CORE.md)
  → Extract X-Organization-Id
  → Permission check via Core public API (or documented workaround until API exists)
  → Product API handler
  → Product use case
  → Product repository (fair_crm DB, org-scoped)
  → Optional: Core audit API call on success
  → HTTP Response
```

Every product use case **must** enforce `organization_id` from validated auth context — never from an unvalidated request body alone.

---

## 10. Application composition

`create_app()` in Fair CRM is responsible for **product concerns only**:

1. Load Fair CRM settings (`DATABASE_URL`, `KYROX_CORE_BASE_URL`, `JWT_SECRET_KEY` for validation).
2. Register product module routers under `/api/v1`.
3. Register product exception handlers and middleware.
4. Wire `integrations/kyrox_core` HTTP client (base URL from config).

Fair CRM **does not** bootstrap Core job handlers, notification registries, or Core Alembic.

---

## 11. Testing strategy

| Layer | Approach |
|-------|----------|
| Domain | Unit tests; no DB, no HTTP |
| Application | Unit tests with fake repositories and fake Core ports |
| Infrastructure | Integration tests against product DB (SQLite CI / PostgreSQL) |
| Integrations | Mock Core HTTP responses; contract tests against Core v0.4.0 in integration env |
| API | `TestClient`; org isolation mandatory |

Run `python scripts/quality_check.py` before PRs.

---

## 12. Reference analysis (`fuar-crm`)

Per ADR-004, legacy **`fuar-crm`** is reference-only.

**Status:** Completed — [FUAR_CRM_REFERENCE_ANALYSIS.md](FUAR_CRM_REFERENCE_ANALYSIS.md).

---

## 13. Core API gaps (report before Phase 2)

Documented in [INTEGRATION_WITH_CORE.md](INTEGRATION_WITH_CORE.md) §9. Summary:

| ID | Gap | Impact |
|----|-----|--------|
| CG-1 | No audit **write** public API | Product cannot emit `fair_crm.customer.*` audit events via API |
| CG-2 | No permission **check** / token introspection API | Product RBAC enforcement strategy incomplete |
| CG-3 | No product permission **registration** API | `fair_crm.customers.*` must be seeded in Core by platform change |
| CG-4 | No product integration guide in Core | Developer onboarding gap |

These are **kyrox-core** deliverables (Sprint 1.0 integration prep). Fair CRM Phase 2 should not start until gaps CG-1–CG-3 have an approved resolution path.

---

## 14. Future evolution

- **SDK:** Optional typed client wrapping Core public APIs (separate package, later).
- **Events:** Async integration (webhooks, message bus) when Core exposes them — not Sprint 1.
- **Service split within Fair CRM:** Internal modular monolith may extract modules later; Core remains a separate platform service regardless.

---

## 15. Phase 1 exit criteria

- [x] Target architecture documented — independent services (this file)
- [x] Core integration via public APIs documented ([INTEGRATION_WITH_CORE.md](INTEGRATION_WITH_CORE.md))
- [x] Customer aggregate designed ([CUSTOMER_DESIGN.md](CUSTOMER_DESIGN.md))
- [x] Core API gaps documented
- [x] Legacy `fuar-crm` reference review — [FUAR_CRM_REFERENCE_ANALYSIS.md](FUAR_CRM_REFERENCE_ANALYSIS.md)
- [ ] CTO review and approval before Phase 2 implementation

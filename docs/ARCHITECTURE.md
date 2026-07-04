# FAIR CRM Architecture

**Status:** Active product architecture - current target: Canonical Import Schema, then Import Batch / Preview / Duplicate / Merge  
**Platform dependency:** kyrox-core **v0.4.0+** (independent platform service)  
**Related:** [INTEGRATION_WITH_CORE.md](INTEGRATION_WITH_CORE.md), [CUSTOMER_DESIGN.md](CUSTOMER_DESIGN.md), [DECISIONS.md](DECISIONS.md)

---

## 1. Purpose

This document defines the target architecture for **FAIR CRM** - the first product on the KYROX platform baseline.

FAIR CRM is active in development. Customer/Fair/Participation foundations exist, Adapter Management is completed, Linked Fairs are completed, Fair -> Adapter relationship is completed, Adapter CRUD is completed, and Run v2 + JSON Handoff is completed. The current technical target is Canonical Import Schema; the following target is the Import Batch / Preview / Duplicate / Merge pipeline.

FAIR CRM is an **independent product service**: its own FastAPI application, its own deployment, and its own product database. **KYROX Core** is a separate, independently deployed **platform service**. The two communicate **only through Core public APIs** (and later SDK/events if needed).

FAIR CRM is organized internally as a **modular monolith** â€” one codebase, one process, layered modules â€” but it is **not** the same service as kyrox-core.

Layering follows [kyrox-core Backend Architecture Standards](../../kyrox-core/docs/BACKEND_ARCHITECTURE_STANDARDS.md) as a **convention reference**, not as an import dependency.

---

## 2. Architectural decisions (summary)

| Decision | Choice | ADR |
|----------|--------|-----|
| Core relationship | Independent platform **service**; public API integration | ADR-007 |
| Product deployment | Independent FastAPI **service** (modular monolith internally) | ADR-008 |
| Core imports | **Forbidden** â€” no `from app.modules...` from kyrox-core | ADR-007 |
| Database | **Separate** product database; no shared SQLAlchemy session with Core | ADR-007 |
| Cross-repo DB coupling | **Forbidden** â€” no shared DB, no FKs to Core tables | ADR-007 |
| Tenancy | `organization_id` (UUID) from Core; logical reference only | ADR-002 |
| Language | English backend/API/DB; Turkish frontend labels | ADR-006 |

---

## 3. System context

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”         HTTP (public APIs)        â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚   Client / Frontend â”‚ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–º â”‚    KYROX Core       â”‚
â”‚                     â”‚   /api/v1/auth/login, orgs, ...   â”‚  (platform service) â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                                   â”‚  port e.g. 8000     â”‚
          â”‚                                               â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
          â”‚  HTTP  /api/v1/customers, ...                            â”‚
          â”‚                                                          â”‚ Core DB
          â–¼                                               â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”         HTTP (public APIs)        â”‚    PostgreSQL       â”‚
â”‚     FAIR CRM        â”‚ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–ºâ”‚   (kyrox_core)      â”‚
â”‚  (product service)  â”‚   audit, settings, jobs, notif.   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
â”‚  port e.g. 8001     â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
          â”‚
          â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚    PostgreSQL       â”‚
â”‚    (fair_crm)       â”‚
â”‚  crm_customers, ... â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Two services, two databases, one auth token.**

Clients typically authenticate via **Core** (`POST /api/v1/auth/login`), then call **Fair CRM** with the same JWT and `X-Organization-Id`. Fair CRM validates the token and checks permissions through Core APIs (see [INTEGRATION_WITH_CORE.md](INTEGRATION_WITH_CORE.md) for gaps).

---

## 4. Repository layout

```text
fair-crm/
â”œâ”€â”€ backend/
â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”œâ”€â”€ main.py                 # Fair CRM FastAPI app â€” product routes only
â”‚   â”‚   â”œâ”€â”€ core/
â”‚   â”‚   â”‚   â”œâ”€â”€ config.py           # FAIR_CRM_* settings; KYROX_CORE_BASE_URL
â”‚   â”‚   â”‚   â”œâ”€â”€ logging.py
â”‚   â”‚   â”‚   â””â”€â”€ exceptions.py
â”‚   â”‚   â”œâ”€â”€ db/
â”‚   â”‚   â”‚   â””â”€â”€ session.py          # Product DB session only
â”‚   â”‚   â”œâ”€â”€ integrations/
â”‚   â”‚   â”‚   â””â”€â”€ kyrox_core/         # HTTP client adapters to Core public APIs
â”‚   â”‚   â”‚       â”œâ”€â”€ client.py
â”‚   â”‚   â”‚       â”œâ”€â”€ auth.py         # JWT validation (shared secret config)
â”‚   â”‚   â”‚       â”œâ”€â”€ audit.py
â”‚   â”‚   â”‚       â”œâ”€â”€ settings.py
â”‚   â”‚   â”‚       â”œâ”€â”€ jobs.py
â”‚   â”‚   â”‚       â””â”€â”€ notifications.py
â”‚   â”‚   â”œâ”€â”€ api/
â”‚   â”‚   â”‚   â””â”€â”€ v1/
â”‚   â”‚   â”‚       â””â”€â”€ router.py       # Product routes only
â”‚   â”‚   â””â”€â”€ modules/                # Product bounded contexts
â”‚   â”‚       â””â”€â”€ customers/
â”‚   â”‚           â”œâ”€â”€ domain/
â”‚   â”‚           â”œâ”€â”€ application/
â”‚   â”‚           â”œâ”€â”€ infrastructure/
â”‚   â”‚           â””â”€â”€ api/
â”‚   â”œâ”€â”€ alembic/                    # Product schema only (crm_* tables)
â”‚   â””â”€â”€ tests/
â”œâ”€â”€ docs/
â”œâ”€â”€ scripts/
â”‚   â””â”€â”€ quality_check.py
â”œâ”€â”€ alembic.ini
â”œâ”€â”€ requirements.txt                # No kyrox-core package dependency
â””â”€â”€ .env.example
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
api â†’ application â†’ domain
infrastructure â†’ domain (implements ports)
integrations/kyrox_core â†’ used by application or api (via ports)
```

Product **domain** must not import HTTP clients or Core response types. Core integration is behind **ports** implemented in `integrations/kyrox_core/`.

---

## 6. Product module boundaries

| Module | Sprint | Scope |
|--------|--------|-------|
| **customers** | 1.0.0 | CRM account aggregate; org-scoped CRUD |
| **contacts** | 1.1.0 | People linked to customers |
| **fairs** | 1.2.0 | Fair events |
| **participations** | 1.3.0 | Customer â†” fair participation |
| **import** | 1.4.0 | Import pipeline, duplicate detection |
| **scraper** | 1.5.0 | Scraper integration |
| **reporting** | deferred | Reports and export |

**Cross-module rules:**

- Modules communicate via application services â€” not cross-infrastructure imports.
- Shared product primitives (if needed) go under `backend/app/shared/`.
- Each module owns `crm_*` tables in the **fair_crm** database.

---

## 7. Database strategy

### Separate databases â€” no cross-repository coupling

| Service | Database | Tables | Migrations |
|---------|----------|--------|------------|
| **kyrox-core** | `kyrox_core` (example) | `identity_*`, `audit_logs`, `platform_*` | Core Alembic through `20260701_0025` |
| **fair-crm** | `fair_crm` (example) | `crm_customers`, â€¦ | Product Alembic in fair-crm repo |

**Connection:** Fair CRM uses its own `DATABASE_URL` and SQLAlchemy `Session`. Core uses its own â€” **no shared session, no shared connection pool.**

**Organization reference:** Product tables store `organization_id` (UUID) issued by Core. This is a **logical tenant key**, not a foreign key to `identity_organizations`. Fair CRM validates that the caller's org context is authorized via Core APIs before trusting the value.

**Naming:** Product tables use the `crm_` prefix.

---

## 8. API surface

### Fair CRM service (product only)

Base URL: e.g. `http://localhost:8001/api/v1`

| Route group | Examples |
|-------------|----------|
| Health | `GET /health` |
| Customers | `POST /customers`, `GET /customers`, â€¦ |

Fair CRM **does not** expose Core platform routes. Auth, org management, and platform services are on the **Core base URL** (e.g. `http://localhost:8000/api/v1`).

### KYROX Core service (platform)

Documented in [kyrox-core README](../../kyrox-core/README.md). Clients and Fair CRM integration layer call Core directly for platform operations.

---

## 9. Request pipeline (Fair CRM)

```text
HTTP Request â†’ Fair CRM
  â†’ JWT validation (local decode using configured JWT secret â€” see INTEGRATION_WITH_CORE.md)
  â†’ Extract X-Organization-Id
  â†’ Permission check via Core public API (or documented workaround until API exists)
  â†’ Product API handler
  â†’ Product use case
  â†’ Product repository (fair_crm DB, org-scoped)
  â†’ Optional: Core audit API call on success
  â†’ HTTP Response
```

Every product use case **must** enforce `organization_id` from validated auth context â€” never from an unvalidated request body alone.

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

**Status:** Active product architecture - current target: Canonical Import Schema, then Import Batch / Preview / Duplicate / Merge  

---

## 13. Historical Core API Gaps

Documented in [INTEGRATION_WITH_CORE.md](INTEGRATION_WITH_CORE.md) Â§9. Summary:

| ID | Gap | Impact |
|----|-----|--------|
| CG-1 | No audit **write** public API | Product cannot emit `fair_crm.customer.*` audit events via API |
| CG-2 | No permission **check** / token introspection API | Product RBAC enforcement strategy incomplete |
| CG-3 | No product permission **registration** API | `fair_crm.customers.*` must be seeded in Core by platform change |
| CG-4 | No product integration guide in Core | Developer onboarding gap |

These were **kyrox-core** deliverables during the original Sprint 1.0 integration preparation. CG-1 through CG-4 are now resolved for the current integration baseline; keep this section as historical context for why Fair CRM integrates through public Core APIs.

---

## 14. Future evolution

- **SDK:** Optional typed client wrapping Core public APIs (separate package, later).
- **Events:** Async integration (webhooks, message bus) when Core exposes them â€” not Sprint 1.
- **Service split within Fair CRM:** Internal modular monolith may extract modules later; Core remains a separate platform service regardless.

---

## 15. Historical Phase 1 exit criteria

This section is historical. It records the original architecture/design exit criteria from the early Sprint 1.0 phase; it is not the current product state.

- [x] Target architecture documented â€” independent services (this file)
- [x] Core integration via public APIs documented ([INTEGRATION_WITH_CORE.md](INTEGRATION_WITH_CORE.md))
- [x] Customer aggregate designed ([CUSTOMER_DESIGN.md](CUSTOMER_DESIGN.md))
- [x] Core API gaps documented
- [x] Legacy `fuar-crm` reference review â€” [FUAR_CRM_REFERENCE_ANALYSIS.md](FUAR_CRM_REFERENCE_ANALYSIS.md)
- [ ] CTO review and approval before Phase 2 implementation



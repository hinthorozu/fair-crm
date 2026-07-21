# FAIR CRM â€” Integration with KYROX Core

**Status:** Active integration baseline - Core gaps CG-1 through CG-4 resolved  
**Platform dependency:** kyrox-core **v0.4.0+** (independent platform service)  
**Related:** [ARCHITECTURE.md](ARCHITECTURE.md), [DECISIONS.md](DECISIONS.md) ADR-007

---

## 1. Integration model

KYROX Core is an **independent reusable backend platform service**. FAIR CRM is an **independent product service**. Integration is **exclusively through Core public HTTP APIs** (and later SDK/events when available).

FAIR CRM is active in development. The original Sprint 1.0 design notes in this document are historical where they describe unresolved Core gaps; the current baseline uses Core public APIs for authorization checks and audit writes.

| Approach | Decision |
|----------|----------|
| Call Core public REST APIs | **Yes** |
| Import kyrox-core Python packages (`app.modules.*`, etc.) | **No** |
| Share SQLAlchemy Session / database with Core | **No** |
| Mount Core routers inside Fair CRM app | **No** |
| Duplicate platform logic in fair-crm | **No** |
| Local JWT signature validation (shared secret config) | **Yes** â€” not a Core import; validates tokens Core issued |

This aligns with ADR-007 and kyrox-core [Backend Architecture Standards Â§12](../../kyrox-core/docs/BACKEND_ARCHITECTURE_STANDARDS.md): *"Products integrate via public API and documented contracts."*

---

## 2. Runtime topology

| Component | Default local (process) | Responsibility |
|-----------|-------------------------|----------------|
| **KYROX Core** | `http://127.0.0.1:8000` | Auth, orgs, memberships, audit query, settings, jobs, notifications |
| **Fair CRM** | `http://127.0.0.1:8001` | Customer and future CRM domain APIs |
| **Core database** | `postgresql://.../kyrox_core` | Platform schema only |
| **Product database** | `postgresql://.../fair_crm` | `crm_*` tables only |

Process URLs above are for **server-internal** use (backend→Core, health, curl). The browser uses relative paths only — see §4 and [DEV_RUNTIME.md](DEV_RUNTIME.md#browser--frontend-network-local--server).

### Fair CRM configuration

| Setting | Purpose |
|---------|---------|
| `KYROX_CORE_BASE_URL` | Backend HTTP client → Core (e.g. `http://127.0.0.1:8000`) — **not** a browser URL |
| `JWT_SECRET_KEY` | Must match Core — local access-token signature validation |
| `JWT_ALGORITHM` | Must match Core (default `HS256`) |
| `DATABASE_URL` | **Fair CRM database only** |

Fair CRM `requirements.txt` does **not** list kyrox-core as a Python dependency.

---

## 3. Integration layer structure

All Core communication lives in `backend/app/integrations/kyrox_core/`:

```text
integrations/kyrox_core/
â”œâ”€â”€ client.py           # Base HTTP client (httpx), auth header injection, error mapping
â”œâ”€â”€ auth.py             # JWT decode/validate; no Core imports
â”œâ”€â”€ authorization.py    # Permission check port â†’ Core API (when available)
â”œâ”€â”€ audit.py            # Audit write port â†’ Core API (when available)
â”œâ”€â”€ settings.py         # Settings read/write â†’ Core API
â”œâ”€â”€ jobs.py             # Enqueue/status â†’ Core API
â””â”€â”€ notifications.py    # Send/status â†’ Core API
```

Application use cases depend on **ports** (protocols). Infrastructure implements ports via HTTP adapters. Domain layer never calls HTTP directly.

---

## 4. Authentication flow

### 4.1 Login (browser → Core via relative path)

The SPA authenticates through the same-origin Core proxy (not a direct `:8000` URL):

```http
POST /kyrox-core/api/v1/auth/login
Content-Type: application/json

{"email": "...", "password": "..."}
```

- `VITE_CORE_BASE_URL` empty → frontend base `/kyrox-core`
- Local: Vite `/kyrox-core` → `http://127.0.0.1:8000`
- Server: Nginx `/kyrox-core` → `http://127.0.0.1:8000`

Response: `access_token`, `refresh_token` (Core contract).

Token refresh and logout also go to Core under `/kyrox-core/api/v1/auth/...`. Fair CRM does not implement auth issuance endpoints.

Server-side tools (curl, E2E scripts) may still call `http://127.0.0.1:8000/api/v1/auth/login` directly — that is not the browser path.

### 4.2 Calling Fair CRM (browser → product via relative path)

```http
GET /api/v1/customers
Authorization: Bearer <access_token>
X-Organization-Id: <organization_uuid>
```

- `VITE_API_BASE_URL` empty → same-origin `/api/v1/...`
- Local: Vite `/api` → `http://127.0.0.1:8001`
- Server: Nginx `/api` → `http://127.0.0.1:8001`

The browser **never** uses `http://127.0.0.1:8000` or `http://127.0.0.1:8001` as an API base. New host/IP/domain does not require frontend base URL changes.

### 4.3 Token validation (Fair CRM â€” local)

Fair CRM validates JWT **locally** using configured `JWT_SECRET_KEY` and `JWT_ALGORITHM` (same values as Core). This is configuration alignment, not a Python import from kyrox-core.

**Claims used:**

| Claim | Use |
|-------|-----|
| `sub` | User id |
| `email` | User email |
| `sid` | Session id (for audit metadata) |
| `exp`, `iat`, `jti` | Expiry and replay hygiene |

**Organization is not in JWT.** Tenant context comes from `X-Organization-Id` header (Core convention).

### 4.4 Organization context

Every org-scoped Fair CRM request requires:

- Valid Bearer token
- `X-Organization-Id` header matching the organization the user is operating in

Fair CRM passes both when calling Core APIs on behalf of the request.

---

## 5. Authorization (RBAC)

Product routes require product permissions:

| Code | Description |
|------|-------------|
| `fair_crm.customers.read` | List and get customers |
| `fair_crm.customers.create` | Create customers |
| `fair_crm.customers.update` | Update customers |
| `fair_crm.customers.archive` | Archive customers |

### Intended flow

```text
1. Validate JWT locally
2. Read X-Organization-Id
3. Call Core API to verify user has required permission in that organization
4. Proceed or return 403
```

### Historical Core API gap - CG-2

Earlier kyrox-core **v0.4.0** planning identified the need for a dedicated product permission check endpoint. The current integration baseline resolves this through Core's product authorization check API.

**Resolution options (require approval before Phase 2):**

| Option | Description | Owner |
|--------|-------------|-------|
| A | Core adds `POST /api/v1/authorization/check` | kyrox-core |
| B | Core adds token introspection endpoint returning effective permissions | kyrox-core |
| C | Temporary: Fair CRM calls a Core protected route as proxy check (fragile â€” not recommended) | â€” |

**Current status:** Resolved. Fair CRM protected routes use Core's public authorization check API.

### Product permission registration â€” CG-3

Product permissions must exist in **Core's** RBAC store (`identity_permissions`). Product permission registration is owned by Core, not Fair CRM migrations.

**Current status:** Resolved for the customer permission baseline by Core migration `20260701_0025`. Future product permissions remain Core-owned platform changes or admin operations.

---

## 6. Platform capability integration (public APIs)

All endpoints below are on **`{KYROX_CORE_BASE_URL}/api/v1`**. Fair CRM forwards the user's `Authorization` and `X-Organization-Id` unless noted.

### 6.1 Organization and membership

| Operation | Core API | Sprint 1 |
|-----------|----------|----------|
| Create org | `POST /organizations` | Client â†’ Core |
| Get org | `GET /organizations/{id}` | Client â†’ Core |
| List memberships | `GET /organizations/{id}/memberships` | Client â†’ Core |
| Invite member | `POST /organizations/{id}/memberships/invite` | Client â†’ Core |

Fair CRM does not reimplement org/membership lifecycle. Product stores `organization_id` as opaque UUID from Core.

### 6.2 Audit

**Query (available):**

```http
GET /organizations/{id}/audit-logs
Authorization: Bearer ...
X-Organization-Id: ...
```

Requires Core permission `audit.logs.read`. Used by admin UI â€” not by Fair CRM write path.

**Write (resolved integration API - CG-1):**

Product must emit events such as:

- `fair_crm.customer.created`
- `fair_crm.customer.updated`
- `fair_crm.customer.archived`

Per kyrox-platform [ADR-0004](../../kyrox-platform/decisions/0004-audit-service-strategy.md), products emit audit events through **Core contracts**. The current integration baseline exposes a public audit event write API.

Append-only endpoint:

```http
POST /organizations/{id}/audit-events
Authorization: Bearer ...
X-Organization-Id: ...
```

Fair CRM treats audit writes as best-effort: product mutations must not fail solely because audit write is unavailable.

### 6.3 Settings

**Available APIs:**

| Method | Path |
|--------|------|
| `GET` | `/organizations/{id}/settings` |
| `GET` | `/organizations/{id}/settings/{key}` |
| `PUT` | `/organizations/{id}/settings/{key}` |
| `DELETE` | `/organizations/{id}/settings/{key}` |

Requires `settings.platform.read` / `settings.platform.update`.

**Product keys (examples):**

| Key | Purpose |
|-----|---------|
| `fair_crm.customers.default_status` | Default status on create |
| `fair_crm.customers.default_type` | Default customer type |

Fair CRM `integrations/kyrox_core/settings.py` wraps these calls. Schema validation stays in Fair CRM application layer.

### 6.4 Background jobs

**Available APIs:**

| Method | Path |
|--------|------|
| `POST` | `/organizations/{id}/jobs` |
| `GET` | `/jobs/{id}` |

Requires `jobs.platform.enqueue` / `jobs.platform.read`.

Product job types (e.g. `fair_crm.import.process_batch`) are enqueued via Core API with JSON payload. Job **handlers** run in Fair CRM (or a Fair CRM worker process) â€” registered through Core's handler contract when worker architecture is defined. Sprint 1 Customer CRUD does not use jobs.

### 6.5 Notifications

**Available APIs:**

| Method | Path |
|--------|------|
| `POST` | `/organizations/{id}/notifications/send` |
| `GET` | `/notifications/{id}` |

Requires `notifications.platform.send` / `notifications.platform.read`.

Sprint 1 does not send notifications.

---

## 7. Migrations and data ownership

| Repository | Alembic | Database | Content |
|------------|---------|----------|---------|
| kyrox-core | Core chain â†’ `20260701_0025` | Core DB | Platform tables + product permission seeds |
| fair-crm | Product chain | Product DB | `crm_*` tables only |

**Rules:**

- Fair CRM migrations **never** create or alter Core tables.
- Core migrations **never** create CRM tables.
- No cross-database foreign keys.
- Deploy order: Core service + migrations first, then Fair CRM service + migrations.

---

## 8. Error handling

- Map Core HTTP errors (401, 403, 404, 422) to Fair CRM `AppException` at the integration layer.
- Product API error shape should be consistent but is owned by fair-crm â€” not imported from Core code.
- Log Core request failures with correlation id; do not expose Core internals to clients.

### Audit writes (Sprint 1 â€” best-effort)

Fair CRM customer mutations call Core `POST /organizations/{id}/audit-events` after successful persistence. This is **best-effort**:

- Customer create/update/archive **must not fail** only because the audit API is unavailable or returns an error.
- The integration adapter (`integrations/kyrox_core/client.py`) catches HTTP and network failures, logs a **warning**, and returns without raising.
- Operators rely on Core audit query API when writes succeed; failed writes are visible in Fair CRM service logs.

Authorization checks remain **required** â€” permission failures still block protected routes.

---

## 9. Core API Gap Summary

Report to kyrox-core maintainers **before** Fair CRM Phase 2:

| ID | Gap | v0.4.0+ status | Required for Sprint 1 |
|----|-----|----------------|----------------------|
| **CG-1** | Audit event **write** public API | **Resolved** | Yes |
| **CG-2** | Permission **check** API | **Resolved** | Yes |
| **CG-3** | Product permission **registration** (`fair_crm.*`) | **Resolved** â€” Alembic `20260701_0025` | Yes |
| **CG-4** | Product integration guide | **Resolved** | Yes |
| **CG-5** | Identity permission seed completeness | Verify role assignment for E2E | Recommended |
| **CG-6** | Local dev runbook (Core + Fair CRM side-by-side) | Documented in fair-crm README | Recommended |

**Future (not Sprint 1):** SDK package, event bus/webhooks.

---

## 10. What Fair CRM must not do

| Anti-pattern | Reason |
|--------------|--------|
| `import app.modules.identity...` from kyrox-core | Violates service boundary |
| Share `DATABASE_URL` with Core | Cross-repository DB coupling |
| Seed Core `identity_permissions` from Fair CRM migrations | Wrong database and wrong owner |
| Reimplement JWT issuance | Core owns auth |
| Call Core internal/admin endpoints not in public API docs | Fragile coupling |

---

## 11. Sprint 1 integration scope

| Core capability | Integration mechanism | Blocked by |
|-----------------|----------------------|------------|
| Login / refresh / logout | Client â†’ Core API directly | â€” |
| JWT validation | Local (shared secret config) | â€” |
| RBAC on product routes | Core permission check API | â€” |
| Organization context | `X-Organization-Id` header | â€” |
| Audit on customer mutations | Core audit write API (best-effort) | â€” |
| Settings defaults | Core settings API | â€” (optional Sprint 1) |
| Jobs | Core jobs API | Not used Sprint 1 |
| Notifications | Core notifications API | Not used Sprint 1 |

---

## 12. Historical Phase 1 exit criteria

This section is historical. It records the original integration-design exit criteria; CG-1 through CG-4 are resolved in the current Core integration baseline.

- [x] Service-to-service integration model documented
- [x] Auth flow documented (login via Core, JWT on Fair CRM)
- [x] Per-capability public API mapping documented
- [x] Core API gaps documented (CG-1 through CG-6)
- [x] Separate database strategy documented
- [ ] Core gap resolution approved before Phase 2
- [ ] CTO review before Phase 2 implementation



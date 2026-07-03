# Customer Module Design

**Status:** Sprint 1.0.0 Phase 2 — Implementation  
**Module:** `customers`  
**Related:** [ARCHITECTURE.md](ARCHITECTURE.md), [INTEGRATION_WITH_CORE.md](INTEGRATION_WITH_CORE.md), [DOMAIN_MODEL.md](DOMAIN_MODEL.md)

---

## 1. Purpose

`Customer` is the first FAIR CRM aggregate. It represents a CRM account — an organization or business entity that may participate in fairs, appear in imports, receive offers, or be contacted by the sales team.

This document finalizes the Sprint 1.0.0 Customer design for Phase 2 implementation.

**Service boundary:** Customer data lives in the **Fair CRM database**. Platform auth, RBAC, and audit go through **KYROX Core public APIs** — no direct Core imports or shared sessions.

---

## 2. Aggregate overview

```text
Customer (aggregate root)
├── identity: id, organization_id
├── names: display_name, legal_name, trade_name, normalized_name
├── classification: customer_type, status, source
├── contact info: website, phone, email
├── legal/tax: tax_number, tax_office
├── location: country, city, district, address
├── notes: description
└── lifecycle: created_at, updated_at, deleted_at
```

**Tenant rule:** Every customer belongs to exactly one Core **organization** (`organization_id`). The UUID is issued by Core and stored as a logical reference — no FK to Core database tables. Cross-organization access is forbidden.

---

## 3. Domain model

### 3.1 Entity: `Customer`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | UUID | yes | Aggregate id |
| `organization_id` | UUID | yes | Core organization tenant key (opaque UUID) |
| `display_name` | string (1–255) | yes | Primary UI label; preserved as entered |
| `legal_name` | string (0–500) | no | Official registered name |
| `trade_name` | string (0–255) | no | Trading / brand name |
| `normalized_name` | string (1–500) | yes | Derived for matching; not shown as primary label |
| `customer_type` | `CustomerType` | yes | Default `lead` |
| `status` | `CustomerStatus` | yes | Default `lead` |
| `website` | string (0–255) | no | URL or domain fragment |
| `phone` | string (0–50) | no | |
| `email` | string (0–255) | no | Validated format when present |
| `tax_number` | string (0–50) | no | VKN/TCKN etc. |
| `tax_office` | string (0–255) | no | |
| `country` | string (0–100) | no | ISO or free text in v1 |
| `city` | string (0–100) | no | |
| `district` | string (0–100) | no | District / ilçe |
| `address` | string (0–2000) | no | Street address or full address text |
| `description` | string (0–5000) | no | Account-level free-form notes |
| `source` | `CustomerSource` | no | Default `manual`; see §3.6 |
| `created_at` | datetime (UTC) | yes | |
| `updated_at` | datetime (UTC) | yes | |
| `deleted_at` | datetime (UTC) | no | Soft delete; null = active row |

### 3.2 Value object: `CustomerType`

| Value | Meaning |
|-------|---------|
| `exhibitor` | Exhibitor company |
| `visitor` | Visitor organization |
| `supplier` | Supplier |
| `sponsor` | Sponsor |
| `organizer` | Fair organizer |
| `partner` | Business partner |
| `lead` | Unqualified lead (default) |
| `other` | Other account type |

Stored as lowercase string enum in DB.

### 3.3 Value object: `CustomerStatus`

| Value | Meaning |
|-------|---------|
| `lead` | New or unqualified (default) |
| `active` | Active CRM account |
| `inactive` | Temporarily inactive |
| `archived` | Soft-deleted / archived |

**Transitions (Sprint 1):**

```text
lead → active → inactive → archived
lead → archived
active → archived
inactive → active
```

Archived customers have `deleted_at` set and `status = archived`. Restore is out of scope for Sprint 1.

### 3.6 Value object: `CustomerSource`

| Value | Meaning |
|-------|---------|
| `manual` | Created or edited in CRM UI (default) |
| `excel` | Originated from Excel import pipeline |
| `scraper` | Originated from scraper → import pipeline |

Stored as lowercase string enum in DB. Sprint 1 create defaults to `manual`; import/scraper modules set source on commit.

### 3.7 Domain invariants

1. `display_name` must be non-empty after trim.
2. `normalized_name` is computed on create/update from `legal_name` if present, else `display_name` (see Section 5).
3. `organization_id` is immutable after create.
4. Archived customers cannot be updated except idempotent archive.
5. `email` must pass basic email validation when non-empty.
6. `phone`, `email`, and `website` are normalized to canonical form on write (see §5.4).

### 3.8 Domain exceptions

| Exception | When |
|-----------|------|
| `CustomerNotFoundError` | Id not found in organization scope |
| `CustomerAlreadyArchivedError` | Mutating archived customer |
| `InvalidCustomerNameError` | Empty display name |
| `InvalidCustomerEmailError` | Malformed email |

---

## 4. Repository port

```python
# Illustrative port — Phase 2 implementation
class CustomerRepository(Protocol):
    def add(self, customer: Customer) -> Customer: ...
    def get_by_id(self, organization_id: UUID, customer_id: UUID) -> Customer | None: ...
    def update(self, customer: Customer) -> Customer: ...
    def list_by_organization(
        self,
        organization_id: UUID,
        *,
        status: CustomerStatus | None = None,
        customer_type: CustomerType | None = None,
        search: str | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> CustomerListResult: ...
    def find_by_normalized_name(
        self,
        organization_id: UUID,
        normalized_name: str,
        *,
        exclude_id: UUID | None = None,
    ) -> list[Customer]: ...
```

**Org isolation:** Every method requires `organization_id`. Queries always filter `organization_id = :org AND deleted_at IS NULL` unless explicitly querying archived (future).

Persistence uses **Fair CRM database only** — see Section 9.

---

## 5. Name normalization

Normalization supports duplicate detection (full merge workflow in Sprint 1.4). Sprint 1 computes and stores `normalized_name` on every create/update.

### 5.1 Pipeline (deterministic)

Apply in order to the chosen source string (`legal_name` if non-empty, else `display_name`):

1. **Trim** leading/trailing whitespace.
2. **Turkish character fold** — map İ→I, ı→i, Ş→S, ş→s, Ğ→G, ğ→g, Ü→U, ü→u, Ö→O, ö→o, Ç→C, ç→c.
3. **Uppercase** (ASCII).
4. **Legal suffix removal** — strip trailing tokens (repeat until stable):

   | Suffix variants |
   |-----------------|
   | `ANONIM SIRKETI`, `A.S.`, `A.Ş.`, `AS`, `LTD.`, `LTD STI`, `LIMITED SIRKETI` |
   | `TICARET`, `TIC.`, `SANAYI`, `SAN.` (only when trailing) |

5. **Punctuation removal** — remove `.`, `,`, `-`, `'`, `"`.
6. **Whitespace collapse** — multiple spaces → single space.

### 5.2 Examples

| Input | normalized_name |
|-------|-----------------|
| `SİNAN ELEKTRONİK ANONİM ŞİRKETİ` | `SINAN ELEKTRONIK` |
| `Sinan Elektronik A.Ş.` | `SINAN ELEKTRONIK` |

### 5.3 Sprint 1 duplicate detection scope

| Capability | Sprint 1 | Sprint 1.4 |
|------------|----------|------------|
| Store `normalized_name` | **Yes** | Yes |
| Exact match on `normalized_name` (warning on create) | **Optional API flag** | Yes |
| Similarity scoring / fuzzy match | No | Yes |
| Merge workflow | No | Yes |
| Import preview | No | Yes |

**Sprint 1 recommendation:** On create, application layer checks `find_by_normalized_name`. If matches exist, return `201` with `possible_duplicates` in response metadata (non-blocking). Blocking duplicate policy deferred to import pipeline.

Normalization logic lives in `domain/services/normalizers.py` (pure functions, fully unit tested).

### 5.4 Contact field normalization (on create/update)

Applied when the corresponding field is present:

| Field | Rules |
|-------|-------|
| **Phone** | Digits only; Turkish numbers normalized to `90` + 10 digits (handles leading `0`, `90`, or 10-digit local) |
| **Email** | Trim; lowercase |
| **Website** | Trim; strip `http://`, `https://`, `www.`; remove path/query — store domain fragment |

These canonical forms are stored in `phone`, `email`, `website` columns for consistent search and future duplicate matching.

---

## 6. Application use cases

| Use case | Command | Result |
|----------|---------|--------|
| CreateCustomer | `CreateCustomerCommand` | `CustomerResult` + optional duplicate hints |
| GetCustomer | `GetCustomerQuery` | `CustomerResult` |
| ListCustomers | `ListCustomersQuery` | `CustomerListResult` (cursor pagination) |
| UpdateCustomer | `UpdateCustomerCommand` | `CustomerResult` |
| ArchiveCustomer | `ArchiveCustomerCommand` | `CustomerResult` |

### 6.1 CreateCustomer flow

```text
CreateCustomerCommand
  → validate JWT + organization_id from request auth context
  → verify permission via Core API (fair_crm.customers.create) — requires CG-2
  → build Customer entity (compute normalized_name)
  → CustomerRepository.add (fair_crm DB)
  → Core audit API: fair_crm.customer.created — requires CG-1
  → return CustomerResult
```

### 6.2 ListCustomers pagination and search

Cursor-based (aligned with Core audit query API pattern):

- Sort: `created_at DESC`, `id DESC`
- Cursor: opaque base64 of `(created_at, id)`
- Default limit: 50; max: 100

**Search (`search` query param):** Case-insensitive partial match (`ILIKE`) across any of:

| Field |
|-------|
| `display_name` |
| `normalized_name` |
| `legal_name` |
| `trade_name` |
| `country` |
| `city` |
| `district` |
| `address` |
| `website` |
| `phone` |
| `email` |

Search is combined with optional `status` and `customer_type` filters. Archived customers are excluded unless a future `include_archived` flag is added.

### 6.3 UpdateCustomer

- Partial update supported for mutable fields.
- Recompute `normalized_name` when `display_name` or `legal_name` changes.
- Re-normalize `phone`, `email`, `website` when those fields change.
- Core audit API: `fair_crm.customer.updated` with changed fields in payload (no secrets).

### 6.4 ArchiveCustomer

- Set `status = archived`, `deleted_at = now()`.
- Core audit API: `fair_crm.customer.archived`.
- Idempotent if already archived.

---

## 7. Authorization

| Endpoint | Permission |
|----------|------------|
| `GET /customers` | `fair_crm.customers.read` |
| `GET /customers/{id}` | `fair_crm.customers.read` |
| `POST /customers` | `fair_crm.customers.create` |
| `PATCH /customers/{id}` | `fair_crm.customers.update` |
| `DELETE /customers/{id}` | `fair_crm.customers.archive` |

**Enforcement (service boundary):**

1. Fair CRM API layer validates JWT locally (`integrations/kyrox_core/auth.py`).
2. Reads `X-Organization-Id`.
3. Calls Core public API to verify permission (port: `AuthorizationPort`) — **blocked until CG-2 / CG-3 resolved**.
4. Passes `organization_id` and `user_id` into use cases.

Permissions are stored and evaluated in **Core**, not in the Fair CRM database.

---

## 8. API design

**Service:** Fair CRM (`{FAIR_CRM_BASE_URL}/api/v1`)  
**Auth:** Bearer token from Core login; `X-Organization-Id` header.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/customers` | Create customer |
| `GET` | `/customers` | List with filters (`status`, `customer_type`, `search`, `cursor`, `limit`) |
| `GET` | `/customers/{id}` | Get by id |
| `PATCH` | `/customers/{id}` | Partial update |
| `DELETE` | `/customers/{id}` | Archive (soft delete) |

Login, refresh, and org management remain on **Core** — not exposed by Fair CRM.

### Request/response schemas (API layer)

- `CreateCustomerRequest` — display_name required; other fields optional
- `UpdateCustomerRequest` — all fields optional
- `CustomerResponse` — full customer DTO
- `CustomerListResponse` — items + next_cursor

Errors: 400 validation, 401 unauthenticated, 403 forbidden, 404 not found (org-scoped).

---

## 9. Persistence

### Database: Fair CRM only

Table `crm_customers` lives in the **fair_crm** PostgreSQL database. Migrations are owned by the fair-crm repository. No reference to Core tables via foreign keys.

### Table: `crm_customers`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `organization_id` | UUID NOT NULL | Indexed; logical Core org reference |
| `display_name` | VARCHAR(255) NOT NULL | |
| `legal_name` | VARCHAR(500) | |
| `trade_name` | VARCHAR(255) | |
| `normalized_name` | VARCHAR(500) NOT NULL | Indexed |
| `customer_type` | VARCHAR(32) NOT NULL | |
| `status` | VARCHAR(32) NOT NULL | |
| `website` | VARCHAR(255) | |
| `phone` | VARCHAR(50) | |
| `email` | VARCHAR(255) | |
| `tax_number` | VARCHAR(50) | |
| `tax_office` | VARCHAR(255) | |
| `country` | VARCHAR(100) | |
| `city` | VARCHAR(100) | |
| `district` | VARCHAR(100) | |
| `address` | TEXT | |
| `description` | TEXT | |
| `source` | VARCHAR(32) NOT NULL DEFAULT 'manual' | `manual`, `excel`, `scraper` |
| `created_at` | TIMESTAMPTZ NOT NULL | |
| `updated_at` | TIMESTAMPTZ NOT NULL | |
| `deleted_at` | TIMESTAMPTZ | |

### Indexes

- `(organization_id, created_at DESC, id DESC)` — list pagination
- `(organization_id, normalized_name)` — duplicate lookup
- `(organization_id, status)` — filter

### Migration

First product revision: `0001_crm_customers.py` in **fair-crm** Alembic only.

Product permission seeds (`fair_crm.customers.*`) belong in **Core** (CG-3) — not in Fair CRM migrations.

---

## 10. Audit events

Emitted via **Core public audit write API**. Sprint 1 behavior is **best-effort** — customer mutations succeed even when audit writes fail; failures are logged as warnings in Fair CRM service logs.

| Action | resource_type | When |
|--------|---------------|------|
| `fair_crm.customer.created` | `customer` | After successful create |
| `fair_crm.customer.updated` | `customer` | After successful update |
| `fair_crm.customer.archived` | `customer` | After archive |

Fair CRM `integrations/kyrox_core/client.py` wraps the HTTP call. Include `user_id`, `session_id` from JWT claims in audit metadata where applicable. Do not store passwords or tokens in audit payloads.

**Query:** Operators use Core `GET /organizations/{id}/audit-logs` directly (requires `audit.logs.read`).

---

## 11. Settings integration (optional Sprint 1)

| Key | Default | Use |
|-----|---------|-----|
| `fair_crm.customers.default_status` | `"lead"` | Override default status on create |
| `fair_crm.customers.default_type` | `"lead"` | Override default customer_type |

Read via Core settings **public API** (`GET /organizations/{id}/settings/{key}`) in `CreateCustomerUseCase`, through `integrations/kyrox_core/settings.py`. If not implemented in Sprint 1, use domain defaults.

---

## 12. Testing plan

| Test file | Coverage |
|-----------|----------|
| `test_customer_name_normalizer.py` | Turkish fold, suffix removal |
| `test_customer_entity.py` | Invariants, status transitions |
| `test_create_customer_use_case.py` | Create flow; mock Core audit/authorization ports |
| `test_customer_repository_integration.py` | Org isolation; fair_crm DB only |
| `test_customers_api_routes.py` | Auth, RBAC (mocked Core), 404 across orgs |
| `test_kyrox_core_client.py` | HTTP adapter contract tests (optional integration env) |

**Mandatory:** Org A user cannot read/update org B customer. Core ports mocked in unit tests; contract tests against real Core in CI integration job when both services run.

---

## 13. Legacy `fuar-crm` reference notes

**Status:** Completed — see [FUAR_CRM_REFERENCE_ANALYSIS.md](FUAR_CRM_REFERENCE_ANALYSIS.md).

Key gaps vs current design: legacy uses `company_name` → fair-crm `display_name`. **Address fields (`district`, `address`, `description`) incorporated in Phase 2.** Multi-value phone/email/website child tables implemented in migration `0020`; performance indexes deferred — see [CUSTOMER_COMMUNICATION_PERFORMANCE.md](CUSTOMER_COMMUNICATION_PERFORMANCE.md).

---

## 14. Out of scope (Sprint 1)

- Contact, Fair, Participation, Import, Frontend UI
- Direct Core Python imports or shared database sessions

---

## 15. Phase 1 exit criteria

- [x] Customer aggregate fields and enums finalized
- [x] Normalization pipeline defined
- [x] Use cases updated for API-based Core integration
- [x] Separate product database documented
- [x] Core API gap dependencies identified (CG-1, CG-2, CG-3)
- [x] Legacy `fuar-crm` field validation — [FUAR_CRM_REFERENCE_ANALYSIS.md](FUAR_CRM_REFERENCE_ANALYSIS.md)
- [x] Core gap resolution approved (CG-1, CG-2 implemented in kyrox-core v0.4.0+)
- [x] CTO review before Phase 2 implementation

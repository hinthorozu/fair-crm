# KYROX Fair CRM — Product Vision

**Status:** Canonical product vision document  
**Scope:** `fair-crm` repository  
**Introduced:** Sprint 09 (2026)

This document describes **where the product is going**, not only where it is today. It complements [PROJECT_STATUS.md](../PROJECT_STATUS.md) (current state) and [PROJECT_CONSTITUTION.md](../PROJECT_CONSTITUTION.md) (development standards).

**Change policy:** Vision and architectural principles should remain stable. Roadmaps, sprint ordering, and feature scope may evolve as business priorities change.

---

## What KYROX Fair CRM Is

KYROX Fair CRM is **not only a CRM**.

Today it is a fair and exhibition relationship management product: customers, contacts, fairs, participations, import, and merge workflows.

**Long-term vision:**

> A **Customer Data Platform** that continuously **acquires**, **enriches**, **verifies**, and **improves** customer information — with human approval at every step that writes to CRM.

The CRM remains the system of record. Everything else feeds it as controlled, previewed, approved data.

---

## Customer Data Lifecycle

Customer information moves through a repeating lifecycle:

```text
Acquire
    ↓
Import
    ↓
Research
    ↓
Enrichment
    ↓
Verification
    ↓
User Approval
    ↓
CRM
    ↓
Sales
    ↓
Repeat
```

| Stage | Purpose |
|-------|---------|
| **Acquire** | Obtain raw data from files, websites, APIs, scrapers, campaigns |
| **Import** | Normalize and map into canonical CRM fields (Universal Import Engine) |
| **Research** | Discover missing facts about known or new companies |
| **Enrichment** | Propose new emails, phones, contacts, websites, social profiles |
| **Verification** | Validate that existing CRM data is still correct and reachable |
| **User Approval** | Operator reviews suggestions; nothing writes without consent |
| **CRM** | Authoritative customer, contact, participation records |
| **Sales** | Business use of trusted data (outreach, fairs, follow-up) |
| **Repeat** | Re-import, re-research, re-verify on a schedule or trigger |

No stage bypasses **User Approval** before persistent CRM updates (except data the user explicitly entered in CRM UI).

---

## Business Workflow

Official business workflow phases drive **development priority** (see [Development Priority](#development-priority)).

### Phase A — Customer Acquisition

**Goal:** Import customer data into CRM.

**Main product:** **Universal Import Engine** (Data Integration module — ADR-016)

Sources include Excel, fair exhibitor lists, CSV, scraper output, and future API/ERP connectors. All paths use preview → decision → apply.

---

### Phase B — Customer Enrichment

**Goal:** Increase customer contact information for existing and newly imported records.

**Version 1 scope:**

- Website Discovery
- Email Discovery
- Phone Discovery
- WhatsApp Discovery (if available)
- Contact Discovery

**Important:** Nothing is written automatically. Every discovery is a **suggestion** until the user approves.

---

### Phase C — Fair Discovery

**Goal:** Discover exhibitors from fair websites and bring them into CRM through the same trusted import path.

```text
Fair Website
    ↓
Scraper
    ↓
Universal Import Engine
    ↓
Preview
    ↓
Decision
    ↓
CRM
    ↓
Customer Enrichment
```

Fair Discovery produces **candidates** for import, not direct CRM rows. After import and approval, Phase B enrichment improves contact coverage.

---

## Development Priority

Development is driven by **business value**, not technical complexity alone. **Within Tier 2**, use this table:

### P0 — Highest business value

| Capability | Phase |
|------------|-------|
| Universal Import Engine | A |
| Website Discovery | B |
| Email Discovery | B |
| Phone Discovery | B |

### P1 — Next wave

| Capability | Phase |
|------------|-------|
| LinkedIn Discovery | B |
| Contact Discovery improvements | B |
| Research Campaigns | B / Intelligence |

### P2 — AI and advanced intelligence

| Capability | Notes |
|------------|-------|
| AI Mapping | Column mapping assistance |
| AI Duplicate Suggestions | Decision support |
| AI Merge Suggestions | Decision support |
| AI Conflict Resolution | Decision support |
| AI Company Summary | Read-only insight |
| Social Discovery | Enrichment |
| Logo Discovery | Enrichment |

P2 features **never** auto-write to CRM. They accelerate human decisions.

---

## Tier-Based Product Delivery

As Fair CRM grows, **all new work** is classified before implementation ([ADR-023](../docs/DECISIONS.md)).

| Tier | Name | What belongs here |
|------|------|-------------------|
| **1** | **Platform Foundation** | Auth, permissions, universal components/engines, backup/scheduler/audit, API & architecture standards |
| **2** | **Business Features** | CRM domain modules — customers, fairs, import, merge, reporting, fair-specific scrapers |
| **3** | **User Experience** | Design system, layout, wizards, modals, themes, a11y, motion, tokens |
| **4** | **Future Vision** | AI, workflow automation, marketplace, multi-tenant, BI, full migration toolkit |

### How Tier interacts with business priority

- **Tier** answers: *What kind of work is this?* (foundation vs feature vs UX vs vision)
- **P0 / P1 / P2** answers: *Among Tier 2 business features, what delivers value first?*
- **Default sprint order:** Tier 1 → Tier 2 → Tier 3 → Tier 4 (product owner may override with documented rationale)

**Planning rule:** New idea → Tier → Roadmap → Sprint. No ad-hoc implementation.

**Tier 1 gate:** Tier 3 UX initiatives do not outrank unresolved Tier 1 foundation unless explicitly waived.

Tier definitions and current snapshot: [PROJECT_STATUS.md § Tier-Based Product Delivery](../PROJECT_STATUS.md)

---

## Long-Term Platforms

Fair CRM evolves as a composition of **independent platforms**, each with a clear boundary:

| Platform | Role |
|----------|------|
| **Universal Import Engine** | Source-agnostic ingest, mapping, matching, preview, apply |
| **Company Intelligence Platform** | Research and enrichment suggestions for existing customers |
| **Data Quality Platform** | Verification and validation of data already in CRM |
| **AI Intelligence Platform** | Decision-support: mapping, duplicates, merge, conflict, classification, summary |
| **Integration Platform** | Connectors: scrapers, REST API, ERP, CSV/XML, sync jobs |
| **System Administration Platform** | Operational tooling: backups, policies, DR, jobs, audit, health |
| **Business Continuity Platform** | Resilience: backup policies, history, retention, restore, off-site copy |

Platforms share patterns (preview-first, background jobs, approval queues) but remain **separately evolvable** modules.

---

## System Administration & Business Continuity

**Purpose:** Operate Fair CRM safely at scale — protect customer data, recover from failure, and prove resilience before high-risk work (import, migration, upgrade).

**Today (shipped):** Admin → System → **Database Backups** — manual backup with format choice (`.dump` DR, `.sql` export, Universal Data Package `.zip` MVP).

**Business Continuity** is the conceptual umbrella under System Administration for everything that keeps data **available, recoverable, and auditable**:

```text
Business Continuity
  Database Backups        ← produces artifacts
  Backup Policies           ← defines when / how many / which format
  Backup Jobs               ← executes policies & triggers
  Backup History            ← Completed / Failed / Skipped audit trail
  Backup Verification       ← integrity beyond pg_restore -l
  Disaster Recovery         ← runbooks & validation
  Restore                   ← controlled .dump recovery only
  Retention Policies        ← policy-scoped cleanup
  Remote / Cloud Backup     ← S3, Azure Blob, GCS, NAS
```

### Backup vs Backup Policy

| Concept | Responsibility |
|---------|----------------|
| **Database Backup** | Run once; produce a file |
| **Backup Policy** | Daily / Weekly / Monthly rules; retention; format; change-detection gate |

Daily policy runs only when `last_data_change > last_successful_backup`; otherwise History records **Skipped — No data changes**.

### Universal Data Package (long-term)

Vendor-independent export (`manifest.json` + entity JSON). Target systems: MSSQL, MySQL, MariaDB, other CRMs. **Migration package, not backup.** Foundation shipped in Sprint 09.2.4; maturity continues under Business Continuity roadmap.

**Roadmap detail:** [PROJECT_STATUS.md § System Administration & Business Continuity Roadmap](../PROJECT_STATUS.md) · **ADR-022**

---

## Company Intelligence

**Purpose:** Research **existing** customers to fill gaps and improve completeness.

**Possible discoveries:**

- Website
- Email
- Phone
- Contact Person
- LinkedIn
- Social Media
- Logo
- Address
- Company Information

**Important:**

> Company Intelligence **NEVER** modifies CRM automatically.

Every finding is a **suggestion** in a review queue. The user approves, rejects, or edits before any CRM write.

---

## Research Campaigns

Future **Research Campaigns** automate *when* to research, not *whether* to write.

| Trigger | Action |
|---------|--------|
| Website exists but email missing | → Research |
| Website exists but phone missing | → Research |
| LinkedIn missing | → Research |
| No contact person | → Research |
| Research older than 180 days | → Research again |
| Customer marked **Do not research** | → Skip |

Campaigns produce suggestion batches; approval rules remain unchanged.

---

## Data Quality Platform

Separate from Company Intelligence.

**Purpose:** Verify **existing** CRM information — correctness and reachability, not net-new discovery.

**Examples:**

- Email Verification (deliverability, format, domain)
- Website Verification (HTTP reachability, redirect, SSL)
- Phone Validation (format, line type where available)
- Scheduled Verification (periodic re-check)
- Verification Campaigns (segment-based, e.g. all customers going to Fair X)

Failed verification creates a **task or flag**, not an automatic field delete or overwrite.

---

## AI Platform

**Philosophy:**

> AI **NEVER** updates CRM automatically.

AI is a **decision-support system**. It proposes; humans dispose.

**Examples:**

| Use case | AI output |
|----------|-----------|
| AI Column Mapping | Suggested source → canonical field map |
| AI Duplicate Suggestions | Ranked match candidates with rationale |
| AI Merge Suggestions | Field-level merge recommendation |
| AI Conflict Resolution | Suggested resolution paths for conflicts |
| AI Company Classification | Industry, size, role tags (suggest only) |
| AI Company Summary | Readable briefing for sales (read-only) |

All AI outputs are logged and auditable. User override is always available.

---

## Product Philosophy

### Business Value First

Development priority is determined by **business workflow** (Phases A → B → C) and the P0 / P1 / P2 table — not by technical novelty or refactor appetite.

### Preview First

No import, scraper output, enrichment, or external API payload is written directly to CRM. Preview and diff are mandatory.

### Human Approval Required

External data and AI suggestions **never** update CRM automatically. Approval is explicit per suggestion, row, or batch.

### Platform Thinking

These capabilities must remain **independent platforms** with clear APIs and boundaries:

- Universal Import
- Company Intelligence
- Data Quality
- AI
- Integration

Shared UX (Veri Entegrasyonu, future intelligence screens) composes platforms; it does not merge them into a monolith.

---

## Team Motto

> **"Kervan yolda düzülür; ama pusulasız yola çıkılmaz."**

**Meaning for this project:**

- Roadmaps may evolve as we learn from fairs, customers, and operations.
- Business priorities may shift between acquisition, enrichment, and quality.
- Ideas may grow — new sources, new AI tools, new campaigns.

What must stay stable is the **compass**: preview-first, human approval, platform boundaries, and the Customer Data Platform lifecycle. [PROJECT_CONSTITUTION.md](../PROJECT_CONSTITUTION.md) and [docs/DECISIONS.md](DECISIONS.md) encode that compass; this document points the direction.

---

## Related Documents

| Document | Relationship |
|----------|--------------|
| [PROJECT_CONSTITUTION.md](../PROJECT_CONSTITUTION.md) | Development standards; incorporates Product Vision principles |
| [PROJECT_STATUS.md](../PROJECT_STATUS.md) | Current sprint and delivery status |
| [docs/DECISIONS.md](DECISIONS.md) | ADRs (e.g. ADR-005 preview, ADR-016 Universal Import, ADR-023 Tier delivery) |
| [docs/import/IMPORT_ARCHITECTURE.md](import/IMPORT_ARCHITECTURE.md) | Universal Import Engine architecture |
| [CHANGELOG.md](../CHANGELOG.md) | Shipped features by version |

---

## Document History

| Date | Sprint | Change |
|------|--------|--------|
| 2026-07-01 | 09 | Initial Product Vision — Customer Data Platform, business phases, platforms, philosophy |
| 2026-07-02 | 09.2.5 | System Administration & Business Continuity roadmap — Admin platform vision, policy engine, DR |
| 2026-07-02 | 09.2.6 | Tier-Based Product Delivery Strategy — Tier 1–4 planning and priority rules (ADR-023) |

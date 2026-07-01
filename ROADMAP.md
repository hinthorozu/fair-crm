# FAIR CRM Roadmap

## Current Phase

FAIR CRM Integration Preparation

The KYROX Core platform baseline is completed and frozen at `v0.4.0`. FAIR CRM development starts as the first product implementation on top of that platform.

## Milestone: Sprint 1.0.0 — Product Foundation & Customer Module

Goal: establish the FAIR CRM repository structure and design the first business aggregate.

### Phase 1 — Design

- [x] Analyze old `fuar-crm` repository as a reference only — [docs/FUAR_CRM_REFERENCE_ANALYSIS.md](docs/FUAR_CRM_REFERENCE_ANALYSIS.md)
- [x] Define target FAIR CRM architecture — [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [x] Define product module boundaries — [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §6
- [x] Design Customer aggregate — [docs/CUSTOMER_DESIGN.md](docs/CUSTOMER_DESIGN.md)
- [x] Design Customer normalization and duplicate-detection strategy — [docs/CUSTOMER_DESIGN.md](docs/CUSTOMER_DESIGN.md) §5
- [x] Define integration points with KYROX Core — [docs/INTEGRATION_WITH_CORE.md](docs/INTEGRATION_WITH_CORE.md) *(revised: public API integration; Core gaps documented)*

### Phase 2 — Implementation

- [x] Create backend module structure
- [x] Implement Customer domain
- [x] Implement Customer application use cases
- [x] Implement Customer persistence
- [x] Add migration
- [x] Add Customer API
- [x] Add tests

## Milestone: Sprint 1.1.0 — Contact Module

- [ ] Contact domain
- [ ] Contact/customer association
- [ ] Contact role and communication fields
- [ ] Contact API

## Milestone: Sprint 1.2.0 — Fair Module

- [ ] Fair domain
- [ ] Fair dates and location
- [ ] Organizer relation
- [ ] Fair API

## Milestone: Sprint 1.3.0 — Fair Participation

- [ ] Customer participation in fairs
- [ ] Hall / stand metadata
- [ ] Exhibitor status lifecycle
- [ ] Participation API

## Milestone: Sprint 1.4.0 — Import Pipeline

- [ ] Import batches
- [ ] Import rows
- [ ] Import preview
- [ ] Duplicate detection
- [ ] Merge decisions
- [ ] Excel import adapter

## Milestone: Sprint 1.5.0 — Scraper Integration

- [ ] Scraper source registry
- [ ] Scraper run tracking
- [ ] Extracted row normalization
- [ ] Import handoff

## Deferred

- File storage
- Advanced caching
- Observability dashboard
- External email provider integration
- WhatsApp integration
- Full reporting module

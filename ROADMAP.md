# FAIR CRM Roadmap

## Current Phase

FAIR CRM Integration Preparation

The KYROX Core platform baseline is completed and frozen at `v0.4.0`. FAIR CRM development starts as the first product implementation on top of that platform.

## Milestone: Sprint 1.0.0 — Product Foundation & Customer Module

Goal: establish the FAIR CRM repository structure and design the first business aggregate.

### Phase 1 — Design

- [ ] Analyze old `fuar-crm` repository as a reference only
- [ ] Define target FAIR CRM architecture
- [ ] Define product module boundaries
- [ ] Design Customer aggregate
- [ ] Design Customer normalization and duplicate-detection strategy
- [ ] Define integration points with KYROX Core

### Phase 2 — Implementation

- [ ] Create backend module structure
- [ ] Implement Customer domain
- [ ] Implement Customer application use cases
- [ ] Implement Customer persistence
- [ ] Add migration
- [ ] Add Customer API
- [ ] Add tests

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

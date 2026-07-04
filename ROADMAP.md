# FAIR CRM Roadmap

This document summarizes the active FAIR CRM product direction. Detailed sprint history and quality status live in [PROJECT_STATUS.md](PROJECT_STATUS.md), which is the canonical project-status document.

## Current State

FAIR CRM is active in development. It is no longer in the initial Sprint 1.0 Customer-only phase.

Completed or present product foundations:

- Customer module
- Fair module
- Customer/Fair Participation foundation
- Adapter Management
- Linked Fairs
- Fair -> Adapter relationship
- Adapter CRUD
- Run v2 + JSON Handoff

Current technical target:

- Canonical Import Schema

Next target:

- Import Batch / Preview / Duplicate / Merge pipeline

## Platform Dependency

FAIR CRM consumes KYROX Core as an independent reusable platform service.

| Dependency | Status |
|------------|--------|
| KYROX Core baseline | v0.4.0+ |
| Product authorization check API | Available |
| Audit event write API | Available |
| FAIR CRM permission seeds | Available in Core migration `20260701_0025` |
| Integration model | Public HTTP APIs only |

FAIR CRM must not import Core Python modules, share the Core database, or mount Core routers.

## Active Roadmap

| Target | Status | Notes |
|--------|--------|-------|
| Customer/Fair/Participation foundation | Completed | Core CRM foundations exist |
| Adapter Management | Completed | Adapter CRUD and management workflow available |
| Linked Fairs | Completed | Fair linkage workflow available |
| Fair -> Adapter relationship | Completed | Fair-specific adapter association available |
| Run v2 + JSON Handoff | Completed | Adapter run output can hand off structured JSON |
| Canonical Import Schema | Current technical target | Normalize handoff payloads into a stable import contract |
| Import Batch / Preview / Duplicate / Merge | Next target | Build the preview-first import decision pipeline |

## Historical Milestones

The original Sprint 1.0 through Sprint 1.5 plan below is historical. It described the early product bootstrap sequence and should not be treated as the live roadmap.

| Historical milestone | Original focus | Current interpretation |
|----------------------|----------------|------------------------|
| Sprint 1.0.0 | Product foundation and Customer module | Superseded by current project status |
| Sprint 1.1.0 | Contact module | Track through PROJECT_STATUS.md |
| Sprint 1.2.0 | Fair module | Foundation exists |
| Sprint 1.3.0 | Fair Participation | Foundation exists |
| Sprint 1.4.0 | Import Pipeline | Reframed as Canonical Import Schema, then Import Batch / Preview / Duplicate / Merge |
| Sprint 1.5.0 | Scraper Integration | Reframed through Adapter Management and Run v2 + JSON Handoff |

## Deferred

- File storage
- Advanced caching
- Observability dashboard
- External email provider integration
- WhatsApp integration
- Full reporting module

Before starting new work, read [PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md), [PROJECT_STATUS.md](PROJECT_STATUS.md), [CHANGELOG.md](CHANGELOG.md), [docs/PRODUCT_VISION.md](docs/PRODUCT_VISION.md), and [docs/DECISIONS.md](docs/DECISIONS.md).

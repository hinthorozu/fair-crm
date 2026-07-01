# FAIR CRM

FAIR CRM is the first product built on top of the KYROX platform baseline.

The product focuses on fair, exhibition, exhibitor, customer, contact, participation, stand, import, scraper, and reporting workflows.

## Repository Role

This repository contains the FAIR CRM product code and product-specific documentation.

Related repositories:

- `kyrox-platform` — project management, roadmap, milestones, architecture notes, and current state.
- `kyrox-core` — platform baseline: Identity, Organization, Membership, Audit, Settings, Background Jobs, Notifications.
- `fair-crm` — FAIR CRM product modules.

## Current Status

- Product status: Not started
- Current phase: FAIR CRM Integration Preparation
- First milestone: Sprint 1.0.0 — Product Foundation & Customer Module
- Platform dependency: `kyrox-core v0.4.0`

## Platform Baseline

FAIR CRM must use KYROX Core for platform concerns:

- Authentication
- Authorization
- Organization and membership
- Audit logs
- Settings
- Background jobs
- Notifications

FAIR CRM must not reimplement these platform capabilities.

## Language Rules

- Backend code: English
- Database names: English
- API paths and schemas: English
- Frontend labels and user-facing messages: Turkish

## Initial Product Modules

Planned product modules:

1. Customer
2. Contact
3. Fair
4. Fair Participation
5. Stand / Hall
6. Import Pipeline
7. Scraper Sources and Runs
8. Notes and Tags
9. Reporting

## First Development Target

The first product aggregate is `Customer`.

Customer represents a CRM account that may be an exhibitor, lead, supplier, sponsor, organizer, partner, or other business entity related to fair workflows.

## Development Workflow

Each sprint follows this pattern:

1. Phase 1 — Design
2. CTO Review
3. Phase 2 — Implementation
4. CTO Review
5. Release / documentation update when needed

Cursor or any AI developer should read these files before implementation:

1. `README.md`
2. `ROADMAP.md`
3. `docs/PRODUCT_VISION.md`
4. `docs/DOMAIN_MODEL.md`
5. `docs/DECISIONS.md`

## Next Step

Start Sprint 1.0.0 Phase 1: FAIR CRM Product Foundation and Customer Domain Design.

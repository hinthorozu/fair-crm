# FAIR CRM Domain Model

## Bounded Contexts

Initial product bounded contexts:

1. Customer Management
2. Contact Management
3. Fair Management
4. Participation Management
5. Import Pipeline
6. Scraper Integration
7. Reporting

## Customer Aggregate

`Customer` is the first aggregate.

A customer may represent:

- Exhibitor
- Lead
- Supplier
- Sponsor
- Organizer
- Partner
- Visitor organization
- Other CRM account

### Candidate Fields

- `id`
- `organization_id`
- `display_name`
- `legal_name`
- `trade_name`
- `normalized_name`
- `customer_type`
- `status`
- `website`
- `phone`
- `email`
- `tax_number`
- `tax_office`
- `country`
- `city`
- `district`
- `address`
- `description`
- `source` (`manual`, `excel`, `scraper`)
- `created_at`
- `updated_at`
- `deleted_at`

### Customer Status

Lifecycle (finalized in Sprint 1.0.0 Phase 1 — see [CUSTOMER_DESIGN.md](CUSTOMER_DESIGN.md)):

- `lead` (default)
- `active`
- `inactive`
- `archived`

### Customer Type

Values (finalized in Sprint 1.0.0 Phase 1):

- `exhibitor`
- `visitor`
- `supplier`
- `sponsor`
- `organizer`
- `partner`
- `lead` (default)
- `other`

## Contact Entity

Contact will be designed after Customer.

Candidate fields:

- `id`
- `customer_id`
- `full_name`
- `title`
- `email`
- `phone`
- `mobile_phone`
- `is_primary`
- `created_at`
- `updated_at`

## Fair Entity

Candidate fields:

- `id`
- `name`
- `slug`
- `starts_at`
- `ends_at`
- `country`
- `city`
- `venue`
- `status`

## Fair Participation

Represents a customer participating in a fair.

Candidate fields:

- `id`
- `fair_id`
- `customer_id`
- `hall`
- `stand`
- `participation_status`
- `source`
- `created_at`
- `updated_at`

## Import Pipeline

Import pipeline will support:

- `ImportBatch`
- `ImportRow`
- Import preview
- Duplicate detection
- Merge decisions
- Row-level validation
- Import status tracking

## Duplicate Detection

Customer matching must support:

- Turkish character normalization
- Case normalization
- Legal suffix normalization/removal
- Punctuation cleanup
- Whitespace cleanup
- Similarity scoring
- Possible match suggestions

Example:

`SİNAN ELEKTRONİK ANONİM ŞİRKETİ`

should match possible variants like:

`SINAN ELEKTRONIK A.Ş.`

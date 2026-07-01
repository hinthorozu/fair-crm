# Data Integration — Merge Rules

**Status:** Architecture (Sprint 09.0)  
**Applies to:** Universal Import Standard (ADR-016)  
**Related:** [MATCHING_RULES.md](MATCHING_RULES.md), [IMPORT_ARCHITECTURE.md](IMPORT_ARCHITECTURE.md), [IMPORT_WIZARD_MERGE_RULES.md](../IMPORT_WIZARD_MERGE_RULES.md) (Sprint 07 baseline)

These rules govern how import data is merged into existing CRM records during **Preview → Decision → Apply**. They extend Sprint 07 merge behavior and apply to all source types.

---

## Core principle

**Import never blindly overwrites CRM data.** Merge is additive and conservative by default. The user sees field-level diffs and confirms decisions before apply.

---

## Customer field merge

| Scenario | Rule |
|----------|------|
| CRM field **populated**, import **empty** | **Keep CRM** — import does not clear |
| CRM field **empty**, import **has value** | **Fill from import** |
| CRM field **populated**, import **different value** | **Conflict** — mark for manual review unless user explicitly chooses overwrite for that field/row |
| CRM field **populated**, import **same value** (normalized) | **No change** — show as “Aynı” in merge preview |

### Never overwrite by default

- Existing customer `display_name`, address, country, city, website, notes, etc. are **not** replaced by conflicting import values without explicit user decision.
- Empty incoming values **never** null out populated CRM fields.

---

## Email merge (additive)

| Rule | Detail |
|------|--------|
| Additive | New emails from import are **added** to the customer email set |
| Deduplication | Same email (normalized: lowercase, trimmed) is **not** added twice |
| Multi-email | Import may contain `;` or `,` separated lists; each token normalized and merged |
| Primary email | Import does not change primary email unless user explicitly selects that action |
| Cross-field | Email appearing in `phone` or `website` column is not auto-promoted without mapping |

Uses existing multi-email normalizer from Customer module.

---

## Phone merge (additive)

| Rule | Detail |
|------|--------|
| Additive | New phone numbers are **added** to customer phone collection (when Customer Phones module is active) |
| Deduplication | Same phone (normalized digits) is **not** added twice |
| Empty import phone | No effect on existing phones |
| Conflict | Different formatting of same number → treat as duplicate after normalization |

Until Customer Phones sprint ships, phone merge rules are documented here and applied when the phone model is available.

---

## Contact merge (additive)

| Rule | Detail |
|------|--------|
| New contact | Create `Contact` when import row includes contact fields and user decision is `create_new` or update with new contact |
| Existing contact match | Match by email or name within same customer; merge fields per same populated/empty rules |
| Additive emails on contact | Same dedupe rules as customer email |
| No silent contact delete | Import never removes existing contacts |

---

## Fair participation merge

| Scenario | Rule |
|----------|------|
| Customer exists, **no** participation for batch fair | **Create** `CustomerFairParticipation` with hall/stand/status from import |
| Participation exists | Update hall/stand/notes only per merge rules (empty import does not clear) |
| Excel **only company name** | **Customer unchanged**; only participation created/updated for batch fair |
| No customer match | `create_new` decision creates customer **and** participation |

Hall and stand exist **only** on `CustomerFairParticipation` (ADR-010, ADR-012).

---

## Company-name-only rows

When the mapped import row contains **only** `company_name` (all other canonical fields empty after normalization):

1. If customer matched → **do not modify** customer scalar fields.
2. Ensure participation for batch `fair_id`:
   - Create if missing
   - Skip participation field updates if import has no hall/stand
3. Preview shows action as **“Yalnızca katılım”** / participation-only

This supports exhibitor lists that are name-only.

---

## Conflicting information

When normalized import and CRM values **conflict** on the same field:

| Handling | Detail |
|----------|--------|
| Row status | `conflict` or `manual_review` |
| Preview badge | **Çakışıyor** |
| Default decision | **No auto-apply** — user must resolve |
| Field-level override | User may choose “Import değerini kullan” per field in merge viewer (Sprint 07.1+) |
| Audit | Applied overwrites logged in apply report |

Examples of conflict:

- Different company name for high-confidence email match
- Different country/city with same normalized company name
- Hall/stand mismatch on existing participation (informational, not blocking unless policy requires review)

---

## Skip and invalid rows

| Status | Apply behavior |
|--------|------------------|
| `skip` | Row not applied |
| `invalid` | Row not applied; validation errors shown in final report |
| `manual_review` | Row not applied until decision changed |

---

## Bulk merge defaults

| Bulk action | Behavior |
|-------------|----------|
| Tümünü yeni kabul et | All unmatched → `create_new` |
| Tüm güncellemeleri onayla | All update candidates → `update_existing` with conservative field merge |
| Tümünü atla | All → `skip` |

Bulk actions never bypass conflict rows without explicit confirmation.

---

## Apply transaction policy

| Policy | Default |
|--------|---------|
| Row errors | **Continue** — collect failures, apply remaining rows |
| Batch rollback | Not automatic; operator may re-run after fix |
| Idempotency | Re-apply same batch with same decisions must not duplicate records |

---

## Merge preview display (Turkish labels)

Aligns with Sprint 07.1 merge viewer:

| Outcome | Label |
|---------|-------|
| Same value | Aynı |
| New value on empty CRM field | Eklenecek |
| Update existing | Güncellenecek |
| Conflict | Çakışıyor |
| Preserved CRM value | Korunacak |
| New entity | Yeni |

---

## Versioning

| Version | Sprint | Notes |
|---------|--------|-------|
| 1.0 | 07 / 07.1 | Smart Import Wizard merge rules |
| 2.0 | 09.0 | Universal Import Standard — formalized, source-agnostic |

Implementation must remain backward compatible with existing import batches until migration sprint.

# Smart Import Wizard — Merge Rules

**Status:** Design (Functional Design Phase)  
**Companion:** [IMPORT_WIZARD_FUNCTIONAL_SPEC.md](IMPORT_WIZARD_FUNCTIONAL_SPEC.md)  
**Applies at:** Screen 8 (Apply)  
**Builds on:** ADR-012 (Fair context required for imports)
**Implementation:** Forbidden until approved

---

## 1. Purpose

This document defines **exact field-level merge behavior** when import apply writes to CRM entities. Rules enforce ADR-005 (no blind merge), ADR-010 (hall/stand on participation), and ADR-012 (batch Fair context).

**Entity groups (Fair-scoped import):**

| Entity | Mergeable fields |
|--------|------------------|
| **Customer** | Firma adı (`display_name`), email, telefon, website, ülke, şehir, adres, vergi no |
| **CustomerFairParticipation** | Hall, stand, participation status, notes |
| **Contact** | Yetkili adı, soyadı, ünvanı, email, telefon |

**Critical rule:** Boş incoming alanlar mevcut dolu DB alanlarını silmemelidir (R-02 Keep existing).

**Default philosophy:** **Conservative merge** — fill empty CRM fields from incoming data; never overwrite non-empty CRM values without explicit future override (not in v1 wizard).

---

## 2. Rule Notation

```text
DB      = existing CRM record value (may be null/empty)
IN      = incoming normalized import value (may be null/empty)
OUT     = resulting stored value
```

Empty means: `null`, `""`, or whitespace-only after trim.

---

## 3. Universal Field Merge Matrix

Applies to **Customer**, **Contact**, and **CustomerFairParticipation** scalar fields unless overridden below.

| DB state | IN state | OUT | Rule ID |
|----------|----------|-----|---------|
| empty | empty | empty | R-00 |
| empty | populated | IN | **R-01 Fill empty** |
| populated | empty | DB | **R-02 Keep existing** |
| populated | populated | DB | **R-03 Keep existing (no overwrite)** |

**R-03 is the critical default:** two non-empty values → **keep DB**; incoming value discarded for that field; optional warning on row: “Mevcut değer korundu: {field}”.

### 3.1 Exception — company display name on create

On **create_new**, all populated incoming fields write as-is (no DB yet).

### 3.2 Exception — company_name on update

| DB | IN | OUT | Notes |
|----|-----|-----|-------|
| populated | populated (different) | DB | R-03; original display name preserved |
| populated | populated (same normalized) | DB | no-op |

Normalized name used only for **matching**, not for overwriting display name automatically.

---

## 4. Customer Entity Rules

### 4.1 Applicable fields

`display_name` (from `company_name`), `email`, `phone`, `mobile_phone`, `website`, `country`, `city`, `address`, `tax_number`, status fields (never from import in v1).

**Note (ADR-012):** Mapped import field `notes` applies to **CustomerFairParticipation.notes** (participation scope), not `Customer.notes`. See §5.

### 4.2 Create (`create_new`)

| Field | Rule |
|-------|------|
| All populated incoming | Set on new Customer |
| Empty incoming | Stored as null |
| `status` | Default `active` (or org default) |
| `display_name` | From `company_name` incoming (preserve original casing/spacing from normalized pipeline’s display preservation — see §4.6) |

### 4.3 Update (`update_existing`)

Apply universal matrix R-01..R-03 per field.

**Archived customer:** Apply **fails** for row; error code `customer_archived`; decision forced to skip on retry.

### 4.4 Fields never updated by import (v1)

| Field | Behavior |
|-------|----------|
| `id`, `organization_id`, `created_at` | Immutable |
| `archived_at`, `deleted_at` | Never touched |
| `status` | Never changed by import |

### 4.5 Display name vs normalized name

- **Matching** uses normalized company name (Turkish char folding, legal suffix removal — existing v1 normalizer).
- **Storage** on create uses **incoming raw display** (trimmed), not normalized form, unless user has no raw (then normalized).
- **Update** does not replace display_name when CRM already has one (R-03).

### 4.6 Multi-email (`email` field)

See §8 — special merge, not plain R-03.

---

## 5. CustomerFairParticipation Rules (ADR-010, ADR-012)

Hall, stand, participation status, and participation notes **must not** be written on Customer or Fair. They belong on **CustomerFairParticipation** for the batch-selected Fair.

### 5.1 Preconditions

Participation apply runs when:

1. Row decision is `create_new` or `update_existing`
2. Batch has `fair_id` set (Screen 3 — mandatory)
3. Customer apply succeeded (participation always tied to batch Fair for non-skipped rows)

There is no `fair_name` resolution from source data. Fair context comes exclusively from batch `fair_id`.

### 5.2 Fair context

| Input | Action |
|-------|--------|
| Batch `fair_id` | Always used for participation create/update |
| Row `hall` / `stand` | Merged onto participation per §5.4 |
| Source `fair_name` | **Not supported** — ignored if present in raw data |

### 5.3 Participation create

When no active participation exists for (customer_id, batch `fair_id`):

| Field | Source |
|-------|--------|
| `customer_id` | From customer apply result |
| `fair_id` | Batch `fair_id` |
| `hall` | IN or null |
| `stand` | IN or null |
| `participation_status` | Default `exhibitor` (or IN if future mapping enabled) |
| `notes` | IN `notes` (from mapped import field) or null |
| `primary_contact_id` | Set if contact created/matched in same row (optional v1) |

### 5.4 Participation update

When participation exists (same customer + batch `fair_id`, active):

| Field | DB | IN | OUT |
|-------|-----|-----|-----|
| `hall` | empty | populated | IN (R-01) |
| `hall` | populated | populated | DB (R-03) |
| `hall` | populated | empty | DB (R-02) |
| `stand` | empty | populated | IN (R-01) |
| `stand` | populated | populated | DB (R-03) |
| `stand` | populated | empty | DB (R-02) |
| `participation_status` | any | populated | IN only if DB empty (R-01); else DB (R-03) in v1 |
| `notes` | empty | populated | IN (R-01) |
| `notes` | populated | populated | DB (R-03) |
| `notes` | populated | empty | DB (R-02) |

### 5.5 Customer without hall/stand

Import row with only `company_name` → Customer created/updated **and** participation record created for batch Fair (with null hall/stand). Participation links customer to the selected Fair even when booth data is absent.

---

## 6. Contact Rules

### 6.1 When contact apply runs

Contact pipeline triggers when **any** contact canonical field is populated:

`contact_first_name`, `contact_last_name`, `contact_title`, `contact_department`, `contact_email`, `contact_phone`, `contact_mobile_phone`

### 6.2 Contact matching (update path)

Search existing contacts for customer:

1. Exact match on normalized full name (first + last)
2. Else if only `contact_email` present: match contact with overlapping email
3. Else: **create new** contact

### 6.3 Contact create

| Field | Rule |
|-------|------|
| Populated incoming | Set on new Contact |
| Empty incoming | null |
| `is_primary` | true only if customer has no primary contact; else false |

### 6.4 Contact update (matched)

Apply universal matrix R-01..R-03 per field.

**Name fields:** If DB has partial name (only first) and IN adds last → fill empty part (R-01 per sub-field).

### 6.5 Contact without name

If only `contact_email` or `contact_phone` present without names:

- **v1:** Create contact with empty names allowed if at least one of email/phone present; display as email/phone in UI
- Primary contact rule: do not auto-set primary if ambiguous

### 6.6 Customer vs contact email

| Scenario | Rule |
|----------|------|
| Row has both `email` and `contact_email` | Customer.email merges per §8; contact gets contact_email separately |
| Same address in both | Allowed; de-duplication only within each entity field |

---

## 7. Activity Rules

### 7.1 v1 wizard (minimum)

On successful customer **create** or **update**:

| Field | Value |
|-------|-------|
| `type` | `note` |
| `source` | `import` |
| `subject` | `İçe aktarma` |
| `description` | `Batch {batch_id}, satır {row_index}: {create|update} {company_name}` |
| `customer_id` | affected customer |
| `contact_id` | null (or linked contact if created — optional) |
| `status` | `completed` |

### 7.2 Skip activity when

- Row skipped
- Row failed
- User toggle “Aktivite oluşturma” off (Screen 1, future)

### 7.3 Future (ADR-011)

- Link activity to `participation_id` when participation created/updated
- `type=fair_visit` when fair context present

---

## 8. Multi-Email Merge Rules

Existing v1 behavior **preserved** and extended for wizard transparency.

### 8.1 Canonical storage format

- Separator: `;` (semicolon)
- No spaces around separators after normalize
- Lowercase for duplicate comparison only; preserve display casing in stored string where possible

### 8.2 Normalization pipeline

```text
Raw cell → split on [;,] → trim each → validate format → dedupe case-insensitive → join with ";"
```

Invalid addresses: validation error on row (invalid status); whole row cannot apply unless skipped.

### 8.3 Merge algorithm (Customer.email or Contact.contact_email)

```text
existing_list = parse(DB email)
incoming_list = parse(IN email)
merged_set = ordered_unique(existing_list + incoming_list)  // existing first
OUT = join(merged_set, ";")
```

| Case | Result |
|------|--------|
| DB empty, IN has emails | OUT = IN normalized |
| DB has emails, IN empty | OUT = DB |
| Both have emails | **Union** (not intersection); existing order preserved, new appended |
| Duplicate addresses | Single entry (case-insensitive dedupe) |

**Note:** Multi-email is an **exception to R-03** — incoming emails **append** even when DB already has emails, unless exact duplicate.

### 8.4 Display in merge visualization

Show merged preview:

```text
Mevcut: a@x.com
Gelen:  b@y.com;a@x.com
Sonuç:  a@x.com;b@y.com
```

---

## 9. Decision × Merge Interaction

| User decision | Customer | Participation | Contact | Activity |
|---------------|----------|---------------|---------|----------|
| `create_new` | Create if valid | Create if fair resolved | Create if contact fields | Yes |
| `update_existing` | Update per rules | Update/create per §5 | Update/create per §6 | Yes |
| `skip` | No op | No op | No op | No |

Invalid row + `create_new` attempt: **blocked** at apply validation.

---

## 10. In-Batch Duplicate Rows

When two rows in same batch map to same normalized company name:

| Row | Default suggestion |
|-----|-------------------|
| First occurrence | Normal duplicate detection vs CRM |
| Second occurrence | `skip` with reason `in_batch_duplicate` |

User may override second row to `update_existing` only if CRM match exists (not another row in batch).

---

## 11. Duplicate Detection vs Merge

Duplicate detection operates at **two levels** (ADR-012). Detection **suggests** decisions; merge rules **execute** only after user confirms on Screen 7.

### 11.1 Customer duplicate

| Match confidence | Suggested customer action | User override |
|------------------|--------------------------|---------------|
| 100% exact name | update_existing (if match) / create_new | Allowed |
| 80–99% fuzzy | update_existing | Review recommended |
| < 80% | create_new | User may pick update |

### 11.2 Participation duplicate (within batch Fair)

Evaluated after customer match is resolved:

| Customer in CRM | Participation in batch Fair | Suggested participation action |
|-----------------|----------------------------|-------------------------------|
| No | — | Create Customer + Create Participation |
| Yes | No | Existing Customer + Create Participation |
| Yes | Yes | Existing Customer + Update Participation / Skip row |

Merge rules for Customer, Participation, and Contact apply independently once user decision is confirmed.

---

## 12. Apply Transaction Boundaries

**Per-row atomicity (recommended):**

```text
BEGIN
  upsert Customer
  upsert Participation (if applicable)
  upsert Contact (if applicable)
  insert Activity
  mark ImportRow applied
COMMIT
```

On row failure: ROLLBACK that row; continue others; record error on row.

**Idempotency:** Re-apply same batch rejected if batch status `completed`; row status `applied` skipped on retry.

---

## 13. Field-Level Merge Examples

### Example A — Fill empty phone

```text
DB.phone = null
IN.phone = "+90 212 555 0000"
OUT.phone = "+90 212 555 0000"   (R-01)
```

### Example B — Keep existing website

```text
DB.website = "https://abc.com"
IN.website = "https://abc.com.tr"
OUT.website = "https://abc.com"   (R-03)
Row warning: "website: mevcut değer korundu"
```

### Example C — Hall on participation

```text
DB.participation.hall = "A"
IN.hall = "B"
OUT.participation.hall = "A"   (R-03)
```

### Example D — Empty hall filled

```text
DB.participation.hall = null
IN.hall = "B"
OUT.participation.hall = "B"   (R-01)
```

### Example E — Multi-email union

```text
DB.email = "a@x.com"
IN.email = "b@y.com"
OUT.email = "a@x.com;b@y.com"
```

---

## 14. Validation vs Merge

Validation runs at **Analyze** (Screen 5). Merge runs at **Apply** (Screen 8).

| Validation failure | Merge reached? |
|--------------------|----------------|
| Missing company_name | No — row `invalid` |
| Invalid email format | Row `invalid`; skip only |
| Invalid website URL | Row `invalid` if strict; or warning-only (match v1: invalid) |

Re-validate on apply if batch older than 24h and CRM changed (optional v2).

---

## 15. Logging & Audit

On apply, log per row (Core audit API):

- `import.batch.apply`
- Entity ids created/updated
- Decision taken
- Field warnings (R-03 conflicts count)

Do not log full row PII in application logs.

---

## 16. Future Enhancements (Not v1)

| Enhancement | Description |
|-------------|-------------|
| Per-field overwrite toggle | User picks “gelen veriyi kullan” for website on specific row |
| Merge policy profiles | “Conservative” vs “Overwrite non-empty” org setting |
| Participation status from import | Map column to `participation_status` enum (future) |
| Rollback batch | Store created ids; delete within 24h admin action |

---

## 17. Rule Summary Card (for UX tooltip)

Turkish user-facing summary on Screen 7:

```text
Birleştirme kuralları:
• Boş alanlar gelen veriyle doldurulur.
• Dolu alanlar varsayılan olarak korunur; üzerine yazılmaz.
• Boş gelen veri mevcut dolu alanı silmez.
• E-posta adresleri birleştirilir; tekrarlar kaldırılır.
• Salon, stand ve katılım notları seçilen fuarın katılım kaydına yazılır.
• Fuar, içe aktarma başında seçilir; dosyadan okunmaz.
```

**Implementation:** Implemented in Sprint 07.1 — see `merge_preview` on import row API responses.

---

## 19. Merge visualization (Sprint 07.1)

Preview UI shows field-level diff per row (expand/collapse):

| Alan | CRM | Import | Sonuç |
|------|-----|--------|-------|
| Email | — | info@abc.com | Eklenecek |
| Website | — | www.abc.com | Eklenecek |
| Stand | A12 | A15 | Korunacak (Çakışıyor — R-03) |

Backend `merge_preview.summary_lines` example:

```text
✓ E-posta eklenecek
✓ Website eklenecek
✓ Stand korunacak
```

---

## 18. References

- [IMPORT_WIZARD_FUNCTIONAL_SPEC.md](IMPORT_WIZARD_FUNCTIONAL_SPEC.md)
- [IMPORT_WIZARD_UX_FLOW.md](IMPORT_WIZARD_UX_FLOW.md)
- [IMPORT_ENGINE.md](IMPORT_ENGINE.md)
- [DECISIONS.md](DECISIONS.md) — ADR-005, ADR-010, ADR-012

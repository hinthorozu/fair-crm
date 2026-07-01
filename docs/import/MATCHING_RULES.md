# Data Integration — Matching Rules

**Status:** Architecture (Sprint 09.0)  
**Applies to:** Smart Matching stage ([IMPORT_ARCHITECTURE.md](IMPORT_ARCHITECTURE.md))  
**Related:** [MERGE_RULES.md](MERGE_RULES.md), ADR-016

Matching determines whether an import row relates to an existing **Customer** and/or **CustomerFairParticipation** for the batch fair. Matching is **read-only** until the user confirms decisions.

---

## Matching levels

```text
Import Row (normalized)
    ↓
Level 1 — Customer Match
    ↓
Level 2 — Fair Participation Match (batch fair_id)
    ↓
Combined row status + confidence + suggested action
```

| Level | Question | Entity |
|-------|----------|--------|
| **Customer match** | Does this row refer to an existing customer in the org? | `Customer` |
| **Participation match** | Does this customer already participate in the batch fair? | `CustomerFairParticipation` |

A row may have:

- Customer match only (new participation for this fair)
- Customer + participation match (update candidate)
- No customer match (create new customer + participation)

Fair context is always batch-level `fair_id` (ADR-012). **`fair_name` is never used for matching.**

---

## Company name normalization

Applied to produce **match keys** (not necessarily display values).

| Step | Rule |
|------|------|
| Trim | Leading/trailing whitespace removed |
| Collapse spaces | Multiple spaces → single space |
| Case | Match keys use case-insensitive comparison |
| Turkish folding | See [Turkish character normalization](#turkish-character-normalization) |
| Legal suffix cleanup | See [Legal suffix cleanup](#legal-suffix-cleanup) |
| Punctuation | Remove or normalize `.`, `,`, `'`, `"` for key generation |
| Strip parentheticals | Optional: remove `(…)` trailing qualifiers for key only |

**Display name** for new customers uses original mapped value after light trim, not aggressively stripped legal form unless user template specifies.

---

## Turkish character normalization

For **match key** comparison only:

| Source | Folded |
|--------|--------|
| İ, I, ı, i | `i` |
| Ş, ş | `s` |
| Ğ, ğ | `g` |
| Ü, ü | `u` |
| Ö, ö | `o` |
| Ç, ç | `c` |

Rules:

- Apply Unicode NFKD + Turkish-specific folding table
- Original characters preserved in stored/imported display fields
- Matching is locale-aware (`tr-TR` collation semantics in application layer)

---

## Legal suffix cleanup

Remove or standardize common Turkish and international legal suffixes **for match keys**:

**Turkish examples:** A.Ş., A.S., LTD. ŞTİ., LTD. STI., SAN., TİC., TIC., VE TİC., LTD. ŞTİ., KOLL. ŞTİ., …

**International examples:** LLC, LTD, INC, GMBH, CO., CORP, …

Algorithm (sketch):

1. Tokenize company name
2. Strip trailing legal suffix tokens from a maintained dictionary
3. Rejoin and trim
4. Compare folded keys

Two names that differ only by suffix variant → high name similarity score.

---

## Email matching

| Rule | Detail |
|------|--------|
| Normalization | Lowercase, trim, punycode for IDN domains |
| Multi-email | Any token match counts |
| Exact match | Highest confidence customer signal |
| Domain-only | Not sufficient alone for auto-match (manual review) |
| Shared email across customers | **Manual review** — never auto-merge |

Email match can upgrade a weak name match to strong combined confidence.

---

## Phone matching

| Rule | Detail |
|------|--------|
| Normalization | Strip non-digits; handle leading `0` / country code |
| Exact digit match | Strong signal |
| Truncated / partial | Low signal; not sufficient alone |
| Multiple phones | Match if any normalized phone equals |

Phone matching activates fully when Customer Phones module is available.

---

## Website matching

| Rule | Detail |
|------|--------|
| Normalization | Lowercase host, strip `www.`, default scheme ignored |
| Exact host match | Medium-strong signal |
| Path differences | Host match only for customer-level match |

---

## Customer match strategies (priority order)

1. **Exact email** match (any email on customer)
2. **Exact normalized phone** match
3. **Exact website host** match
4. **Strong company name key** match (post suffix + Turkish fold)
5. **Fuzzy company name** (Levenshtein / token overlap above threshold)
6. **Composite score** — weighted combination of name + email + phone + website

Multiple candidates → rank by score; if top two within margin → **manual review**.

---

## Fair participation match

After customer is resolved (matched or proposed new):

| Condition | Result |
|-----------|--------|
| Customer matched + participation exists for `fair_id` | `participation_match` — update candidate |
| Customer matched + no participation | `participation_new` — create participation only |
| New customer | `participation_new` with customer create |

Participation match uses:

- Same `customer_id` + `fair_id` (unique active constraint)
- Hall/stand are **not** used for identity matching — only customer + fair

---

## Confidence score levels

| Level | Score range | Suggested action | UI badge |
|-------|-------------|------------------|----------|
| **High** | 0.85 – 1.00 | Auto-suggest `update_existing` or `create_new` (user still confirms) | Yüksek eşleşme |
| **Medium** | 0.60 – 0.84 | Suggest action; highlight for review | Orta eşleşme |
| **Low** | 0.30 – 0.59 | Default `manual_review` | Düşük eşleşme |
| **None** | 0.00 – 0.29 | Treat as new unless user overrides | Eşleşme yok |

### Score components (illustrative weights)

| Signal | Weight |
|--------|--------|
| Exact email | 0.45 |
| Exact phone | 0.25 |
| Exact name key | 0.20 |
| Website host | 0.10 |
| Fuzzy name bonus | up to +0.15 |
| Conflicting email on different customer | **Block auto-match** → manual review |

Weights are tunable per organization template in future **Entegrasyon Ayarları**.

---

## Row status mapping

| Status | Meaning |
|--------|---------|
| `new` | No customer match above low threshold |
| `duplicate` | High confidence customer + participation exist; no field changes |
| `update_candidate` | Match found; import adds or changes data per merge rules |
| `conflict` | Match found but conflicting fields |
| `invalid` | Validation failed (missing company_name, bad email format, …) |
| `manual_review` | Operator must decide |

---

## Duplicate detection within batch

Before CRM matching:

- Detect duplicate rows **within the same batch** by normalized company name + email
- Mark duplicates as **batch duplicate** — only first row defaults to apply; others flagged

---

## Performance considerations

With 28k+ customers:

- Matching must use indexed fields (email, normalized name prefix, phone)
- Batch matching runs in background after mapping (analysis job)
- Results paginated in preview UI (server-side list per ADR-015)

---

## Testing requirements (implementation sprint)

- Turkish suffix pairs match
- İstanbul / Istanbul folding
- Email dedupe across multi-email fields
- Company-name-only → participation-only path
- Shared email → manual review
- Confidence threshold boundary cases

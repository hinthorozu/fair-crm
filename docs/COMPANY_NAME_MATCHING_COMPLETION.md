# Company Name Matching Stabilization — Completion Report

**Sprint:** Mission Mode — Company Name Matching Stabilization  
**Date:** 2026-07-02  
**Status:** COMPLETE

---

## Changed Files

| File | Change |
|------|--------|
| `domain/services/company_name_normalizer.py` | Turkish + dotted abbrev + legal suffix phrases + token helpers |
| `domain/services/company_name_matcher.py` | **NEW** — token scoring, confidence bands, explanations |
| `domain/services/duplicate_detector.py` | Token-based index find; `weak_name_candidate`; explanation field |
| `application/import_row_builder.py` | Raw name passed to matcher; `_match_explanation` in normalized JSON |
| `application/analyze_import.py` | Persist `_match_explanation` on rows |
| `tests/modules/imports/test_company_name_matching.py` | **NEW** — sprint dataset |
| `frontend/src/labels/importLabels.ts` | `weak_name_candidate`, explanation labels |
| `frontend/src/pages/ImportWizardPage.tsx` | Show match explanation in decision list |

---

## Normalize Algorithm Summary

1. Turkish char map (İ/I/ı/i, Ş, Ğ, Ü, Ö, Ç → ASCII)
2. NFKD + strip combining marks
3. Lowercase; dots/slashes → spaces (handles `ÜRÜN.GIDA`)
4. Punctuation → spaces; collapse whitespace
5. Iterative removal of **legal suffix phrases** (A.Ş., LTD. ŞTİ., SAN. VE TİC., …)
6. **GIDA** and other sector tokens kept in core (not stripped)

---

## Legal Suffix / Abbreviation Approach

- **Suffix phrases** removed from full normalize key (safe comparison baseline)
- **Core token comparison** excludes `LEGAL_SUFFIX_TOKENS` (san, tic, ltd, anonim, …) but **not** `gida`
- **Abbreviation canonical map**: `san→sanayi`, `tic→ticaret`, `ith→ithalat`, `urun→urunleri`, etc.
- **False-positive guard**: first token mismatch blocks match; same first token + differing tail tokens blocks (ANADOLU GIDA ≠ ANADOLU MAKINA)

---

## Confidence Bands

| Range | Type | Meaning |
|-------|------|---------|
| 95–100 | `exact_normalized_match` | Very strong / normalized exact |
| 85–94 | `fuzzy_name_candidate` | Possible duplicate |
| 70–84 | `weak_name_candidate` | Low confidence — user review |
| <70 | — | No match |

Scoring combines **Jaccard**, **overlap ratio**, and **SequenceMatcher** on core tokens; subset boost when shorter name is contained.

---

## Test Examples

**PASS (high confidence):**
- SİNAN ELEKTRONİK A.Ş. ↔ SINAN ELEKTRONIK ANONIM SIRKETI
- ABC GIDA SAN. VE TİC. LTD. ŞTİ. ↔ ABC GIDA LIMITED SIRKETI
- AGROZAN dotted abbrev ↔ full legal name

**SHOULD NOT MATCH:**
- ABC GIDA ↔ XYZ GIDA
- ANADOLU GIDA ↔ ANADOLU MAKİNA
- BEYDAĞ GIDA ↔ BEYPAZARI GIDA

---

## False Positive Prevention

- First-token mismatch guard (similarity < 82%)
- Distinctive tail mismatch when brand prefix shared
- Minimum score threshold 70
- Prefix-bucket index limits candidate comparisons

---

## Test Results

| Suite | Result |
|-------|--------|
| `tests/modules/imports` | **77 PASS** |
| Frontend `npm run build` | **PASS** |

---

## Known Limits

1. Match explanation stored in `normalized_data_json._match_explanation` (no DB migration)
2. Phone/email/website scoring not implemented (by design)
3. Very short single-token names may still fuzzy-match aggressively
4. CRM `normalized_name` (uppercase customer normalizer) re-normalized via import normalizer in index

---

## Backward Compatibility

- Existing `match_reason` enum values preserved; added `weak_name_candidate`
- Analyzed batches unchanged until re-analyze
- No schema migration required

# UMCRM Data Quality Summary

Generated: 2026-07-01 15:44 UTC
Source: `C:\Users\hinthorozu\Desktop\withdata_u7409970_umycrm.sql`

## Dataset

- Companies: **29,321**
- Emails: **40,240**
- Countries: **2**
- Fairs: **115**
- Fair-company relations: **29,562**

## Issue totals (occurrences)

- Company name issues: **213** (213 rows in CSV)
- Email issues: **9,606** (9,679 rows in CSV)
- Phone issues: **78,139** (78,139 rows in CSV)
- Website issues: **46,489** (46,489 rows in CSV)
- Country issues: **0**
- Fair issues: **253** (253 rows in CSV)
- Relation issues: **715** (714 rows in CSV)

## Top company name issues

- html_entity: 165
- encoding_issue: 48

## Top email issues

- duplicate_cross_company: 8,207
- duplicate_same_company: 885
- case_normalize: 470
- invalid_format: 43
- delimiter_in_email: 1

## Recommended actions (occurrence count)

- KEEP: **118**
- NORMALIZE: **10,456**
- MERGE: **891**
- NULLIFY: **113,793**
- DROP_DUPLICATE_RELATION: **1**
- MANUAL_REVIEW: **10,156**

## Country distribution (top 15)

- Türkiye: 29,321

## Migration notes

- Company duplicate merge (separate report) may create fair participation conflicts — see `merge_conflict` relation issues.
- EmailSubject on fairs is mostly metadata; KEEP when meaningful, NULLIFY placeholders.
- Automatic NULLIFY/DROP is safe for obvious placeholders; MANUAL_REVIEW required for cross-company email duplicates and bad company names.


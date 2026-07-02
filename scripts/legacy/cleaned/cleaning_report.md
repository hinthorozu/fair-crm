# UMCRM Cleaning Report

Generated: 2026-07-02 17:53 UTC
Source: `c:\Users\hinthorozu\Desktop\withdata_u7409970_umycrm.sql`

## Input dataset summary

- Companies: **29,321**
- Emails: **40,240**
- Fairs: **115**
- Relations: **29,562**

## Cleaned output summary

- Companies: **29,321** (all retained, none dropped)
- Company email groups: **29,217**
- Fairs: **115**
- Relations: **29,561**

## Cleaning actions

- Dropped invalid email count: **43**
- Dropped placeholder email count: **0**
- Dropped empty email count: **0**
- Same-company duplicate emails merged: **473**
- Dropped placeholder phone count: **0**
- Dropped invalid website count: **0**
- Dropped placeholder website count: **3**
- Normalized website count: **7,034**
- Nullified fair dates count: **128**
- Manual review companies: **834**
- Manual review fairs: **7**
- Relation duplicate dropped count: **1**
- Relation orphans dropped: **0**

## Key risks

- Company duplicate merge is **not** performed in this script; use duplicate intelligence report before migration.
- Cross-company duplicate emails are preserved but flagged in email group issues.
- Companies with placeholder or encoding-damaged names are kept with `manual_review: true`.
- Fair `EmailSubject` values are preserved in `email_subject_clean` for migration metadata.
- Merge-conflict fair participations must be resolved in a separate merge step.

## Recommended next step

1. Review `manual_review` companies and fairs.
2. Run duplicate merge planning (`analyze_umcrm_duplicates.py` output).
3. Build migration script consuming `scripts/legacy/cleaned/*.json`.
4. Map legacy fair IDs and company IDs to KYROX CRM entities.


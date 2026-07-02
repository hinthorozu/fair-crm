# UMCRM Cleaning Rules Proposal

Recommended actions per issue type. Risky or ambiguous cases are marked **MANUAL_REVIEW**.

## Company name

| Issue | Action | Notes |
| --- | --- | --- |
| empty_name | NULLIFY | Blank name before migration |
| too_short | MANUAL_REVIEW | Length < 2 |
| too_long | MANUAL_REVIEW | Length > 200 |
| digits_only | MANUAL_REVIEW | Not a meaningful company name |
| punctuation_only | MANUAL_REVIEW | Symbols only |
| placeholder | MANUAL_REVIEW or DROP_ROW | test, deneme, null, yok, etc. |
| html_entity | NORMALIZE | Decode HTML entities |
| encoding_issue | MANUAL_REVIEW | Mojibake / replacement chars |

## Email

| Issue | Action | Notes |
| --- | --- | --- |
| empty_email | NULLIFY | |
| placeholder | NULLIFY | test@test.com, noemail, yok |
| invalid_format | MANUAL_REVIEW | Malformed address |
| no_domain | NULLIFY | Missing @ or TLD |
| delimiter_in_email | NORMALIZE | Strip spaces/commas/semicolons |
| case_normalize | NORMALIZE | Lowercase for dedup |
| duplicate_same_company | MERGE | Keep one row per company |
| duplicate_cross_company | MANUAL_REVIEW | Possible shared inbox or duplicate companies |

## Phone

| Issue | Action | Notes |
| --- | --- | --- |
| empty_phone | NULLIFY | |
| placeholder | NULLIFY | 000000, 123456, yok |
| too_short | NULLIFY | < 7 digits |
| all_zeros | NULLIFY | |
| contains_letters | MANUAL_REVIEW | Notes embedded in phone field |
| contains_note | MANUAL_REVIEW | Long or slash-separated values |
| normalize_format | NORMALIZE | Strip formatting chars |
| duplicate_same_company | MERGE | Same digits in Phone1/2/3 |

## Website

| Issue | Action | Notes |
| --- | --- | --- |
| empty_website | NULLIFY | |
| placeholder | NULLIFY | test.com, yok |
| looks_like_email | MANUAL_REVIEW | Move to email if valid |
| looks_like_phone | MANUAL_REVIEW | Move to phone if valid |
| invalid_website | MANUAL_REVIEW | |
| missing_scheme | NORMALIZE | Prefix https:// |
| duplicate_same_company | MERGE | Same host in Web1/Web2 |

## Country

| Issue | Action | Notes |
| --- | --- | --- |
| empty_country_id | NULLIFY | |
| invalid_country_id | MANUAL_REVIEW | FK not in country table |

## Fair

| Issue | Action | Notes |
| --- | --- | --- |
| empty_fair_name | MANUAL_REVIEW | |
| placeholder_fair_name | MANUAL_REVIEW | |
| duplicate_fair_name | MANUAL_REVIEW | May need fair merge |
| suspicious/future dates | NULLIFY | 0000-00-00, 1970-01-01, 2126-01-01 |
| end_before_start | MANUAL_REVIEW | |
| placeholder_fair_area | NULLIFY | |
| empty_fair_area | KEEP | Optional metadata |
| invalid_fair_website | MANUAL_REVIEW | |
| normalize_fair_website | NORMALIZE | |
| email_subject_present | KEEP | Useful for campaign migration context |
| placeholder_email_subject | NULLIFY | |

## Fair-to-company relations

| Issue | Action | Notes |
| --- | --- | --- |
| missing_company | DROP_ROW | Orphan relation |
| missing_fair | DROP_ROW | Orphan relation |
| duplicate_relation | DROP_DUPLICATE_RELATION | Keep one row per (FairId, CompanyId) |
| merge_conflict | MANUAL_REVIEW | After company MERGE, dedupe participations |


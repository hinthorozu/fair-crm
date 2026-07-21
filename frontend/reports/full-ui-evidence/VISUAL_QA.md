# VISUAL_QA

Human visual inspection of screenshots. Criteria: alignment, spacing, form/input width, label-control, checkbox/radio, button hierarchy, table density/columns/actions, toolbar, card/modal width, typography, ultrawide, empty space, stretch, orphan actions, off-screen, clipping, overlap.

## Reviewed (evidence)

| Screenshot | Route | Width | Result | Findings |
|---|---|---:|---|---|
| `screenshots/login__w1440.png` | /login | 1440 | PASS | Focus ring, form width, hierarchy OK |
| `screenshots/customers__w1440.png` | /customers | 1440 | PASS | Table density/actions OK in sample |
| `screenshots/customers__w320.png` | /customers | 320 | PASS | Stacked filters/pagination OK; no H-overflow |
| `screenshots/data-integration_imports_continue_batchId__w1440.png` | continue | 1440 | PASS | Bulk actions inline; primary beside secondary after fix |
| `screenshots/data-integration_imports_continue_batchId__w320.png` | continue | 320 | PASS | DI icon-rail; wizard content above fold after fix |
| `screenshots/data-integration_imports_continue_batchId__w3840.png` | continue | 3840 | FAIL | Ultrawide: large unused horizontal space; content not constrained |

## Not reviewed

All other screenshots under `screenshots/` (~500 files) remain **NOT VERIFIED** for visual criteria.

## Visual failure count (reviewed)

- FAIL: continue ultrawide (2560/3440/3840 sample)
- PASS (sample): login, customers subset, continue 320/1440
- Unreviewed: remainder → NOT VERIFIED


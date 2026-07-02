# Universal Excel Import — Column Mapping Grid + Analysis Queue

**Sprint:** Mission Mode — Column Mapping Preview + Analysis Queue Standard  
**Date:** 2026-07-02  
**Status:** COMPLETE

---

## Summary

Revamped the Universal Excel Import wizard to use an Excel-like column mapping grid, lifecycle-aware Import Jobs list, and background analyze jobs with organization-level concurrency lock.

---

## Changed Files

### Backend
| File | Change |
|------|--------|
| `domain/value_objects.py` | Extended `ImportBatchStatus`, added `ImportJobType.ANALYZE` |
| `domain/batch_status.py` | **NEW** — lifecycle helpers, `GRID_MAPPING_FIELDS` |
| `domain/entities.py` | New batch transition methods (`mark_mapping_completed`, `mark_analysis_queued`, etc.) |
| `domain/exceptions.py` | `ImportAnalyzeInProgressError`, `ImportBatchAnalyzeNotAllowedError` |
| `application/configure_import_header.py` | **NEW** — header step persistence |
| `application/start_import_analyze_job.py` | **NEW** — queue analyze job + org lock |
| `application/import_job_runner.py` | `run_analyze()` background runner |
| `application/analyze_import.py` | Status guards; success → `decision_required` |
| `application/column_mapper.py` | `build_excel_grid_preview()` |
| `application/get_mapping_preview.py` | Returns `grid` payload |
| `api/routes.py` | `PATCH header-config`; sync `POST analyze` deprecated; `analyze-legacy` for tests |
| `data_integration/api/routes.py` | `POST analyze-job` (202) |
| `alembic/versions/0015_import_batch_lifecycle.py` | **NEW** — `mapped`→`mapping_completed`, `applied`→`completed` |

### Frontend
| File | Change |
|------|--------|
| `components/imports/ExcelMappingGrid.tsx` | **NEW** — grid + per-column dropdowns |
| `pages/ImportWizardPage.tsx` | Setup flow: fair → upload → sheet → header → mapping grid → list redirect |
| `pages/DataIntegrationImportsPage.tsx` | Lifecycle status + Analiz Yap / Aç actions |
| `App.tsx` | `/imports/continue/:batchId` route |
| `api/dataIntegration.ts` | `configureImportHeader`, `startImportAnalyzeJob` |
| `labels/importLabels.ts` | New statuses, `WIZARD_SETUP_STEPS`, grid field options |
| `styles.css` | Excel mapping grid + list action styles |

---

## New / Changed Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `PATCH` | `/api/v1/imports/{id}/header-config` | Save header mode (→ `header_configured`) |
| `PATCH` | `/api/v1/imports/{id}/column-mapping` | Save grid mapping (→ `mapping_completed`) |
| `GET` | `/api/v1/imports/{id}/mapping-preview` | Columns + **grid rows** (up to 50) |
| `POST` | `/api/v1/data-integration/imports/{id}/analyze-job` | **Background analyze** (202) |
| `POST` | `/api/v1/imports/{id}/analyze` | Deprecated (400 — use analyze-job) |

---

## Status Transitions

```
uploaded → sheet_selected → header_configured → mapping_completed
  → analysis_queued → analyzing → decision_required
  → applying → completed

analysis_failed (from analyzing, with notes)
failed / cancelled (terminal)
```

Legacy: `mapped` ≡ `mapping_completed`, `applied` ≡ `completed` (migration 0015).

---

## Organization-Level Analyze Lock

- **Where:** `StartImportAnalyzeJobUseCase` + `SqlAlchemyImportJobRepository.has_active_analyze_job()`
- **Rule:** Before creating a new `ANALYZE` job, check org for any job with status `queued` or `running` and `job_type=analyze`
- **On conflict:** HTTP **409** with message: *"Bu organizasyonda devam eden bir analiz işlemi var. Lütfen tamamlanmasını bekleyin."*
- **Per-batch:** Rejects if batch already `analysis_queued` / `analyzing`
- **Test:** `test_start_import_analyze_job.py::test_start_analyze_job_rejects_when_org_has_active_job`

---

## Frontend Mapping Grid

- Excel rows displayed in scrollable table (max 50 preview rows)
- Each column header: letter + optional Excel header + dropdown
- Dropdown options: Kullanma, Firma Adı, Telefon, E-posta, Website, Yetkili Adı, Ülke, Şehir, Adres, Stand No, Salon/Hall, Not
- **Validation:** `company_name` required; duplicate CRM fields disabled in UI; backend enforces uniqueness
- **Save:** Redirects to Import İşleri list (`mapping_completed` → "Analiz Bekliyor")

---

## Import Jobs List

- Lifecycle labels (Analiz Bekliyor, Analiz Ediliyor, Karar Bekliyor, …)
- **Analiz Yap** for `mapping_completed` / `analysis_failed`
- **Aç** for `decision_required` / `analyzed` → continue wizard (decisions → apply → summary)
- Analysis error message shown when `analysis_failed`

---

## Test Results

| Suite | Result |
|-------|--------|
| Backend `tests/modules/imports` + `data_integration` | **74 PASS** |
| Frontend `npm run build` | **PASS** |

---

## Known Gaps

1. Sheet/header steps still optional shortcuts if user uploads single-sheet file (upload auto-selects first sheet)
2. No dedicated preview step in continue flow (decisions step shows merge diff directly)
3. `POST analyze` deprecated but `analyze-legacy` retained for integration tests only
4. Apply-job duplicate prevention not in scope (existing behavior)
5. Worker/Redis queue not used — FastAPI `BackgroundTasks` only

---

## Recommended Next Step

1. **Decision preview table** — server-side DataTable on analyze results before bulk decisions  
2. **Re-analyze** policy — allow explicit re-run after `analysis_failed` only (already supported)  
3. **Mapping templates** — save/load column maps from `crm_import_templates`  
4. **Concurrent analyze UX** — poll org-wide analyze status in list header when job running

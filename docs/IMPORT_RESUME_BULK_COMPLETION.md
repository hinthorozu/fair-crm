# Import Job Resume Flow + Decision Bulk Actions — Completion Report

**Sprint:** Universal Excel Import — Mission Mode  
**Date:** 2026-07-02

---

## Değişen dosyalar

### Backend
- `app/modules/imports/domain/batch_status.py` — setup resume helpers
- `app/modules/imports/domain/services/bulk_decision_actions.py` — **NEW** shared preview/apply logic
- `app/modules/imports/application/preview_bulk_row_decision.py` — **NEW**
- `app/modules/imports/application/start_bulk_row_decision_job.py` — **NEW**
- `app/modules/imports/application/bulk_row_decision.py` — idempotent via shared actions
- `app/modules/imports/application/mappers.py` — batch resume fields
- `app/modules/imports/application/commands.py` — `PreviewBulkDecisionQuery/Result`, batch resume fields
- `app/modules/imports/api/schemas.py` — preview/apply request/response, batch resume fields
- `app/modules/imports/api/routes.py` — bulk preview/apply endpoints
- `app/modules/imports/api/dependencies.py` — preview/start job use cases
- `app/modules/imports/domain/value_objects.py` — `ImportJobType.BULK_DECISION`
- `app/modules/imports/domain/exceptions.py` — bulk/apply in-progress errors
- `app/modules/data_integration/domain/entities.py` — `create_bulk_decision_job`
- `app/modules/data_integration/domain/ports.py` — active bulk/apply job queries
- `app/modules/data_integration/infrastructure/repositories/job_repository.py` — lock helpers
- `app/modules/data_integration/application/import_job_runner.py` — `run_bulk_decision`, `mark_applying`
- `app/modules/data_integration/application/start_import_apply_job.py` — apply lock + `applying` status
- `app/modules/data_integration/api/routes.py` — 409 on concurrent apply
- `tests/modules/imports/test_import_resume_bulk.py` — **NEW**

### Frontend
- `src/utils/importResume.ts` — **NEW** status → wizard step mapping
- `src/pages/DataIntegrationImportsPage.tsx` — Devam Et, setup resume actions
- `src/pages/ImportWizardPage.tsx` — upload redirect, setup/decision resume, bulk preview popup
- `src/api/dataIntegration.ts` — preview/apply bulk API
- `src/types/import.ts` — batch resume fields
- `src/labels/importLabels.ts` — bulk confirm copy
- `src/labels/dataIntegrationLabels.ts` — `continueBatch`
- `src/App.tsx` — upload complete redirect

---

## Yeni endpointler

| Method | Path | Açıklama |
|--------|------|----------|
| `POST` | `/api/v1/data-integration/imports/{batch_id}/bulk-actions/preview` | Etkilenen satır sayısı + özet (veri değiştirmez) |
| `POST` | `/api/v1/data-integration/imports/{batch_id}/bulk-actions/apply` | Toplu karar background job (202) |

Mevcut `PATCH .../rows/bulk-decision` (sync) korundu; UI artık preview + apply job kullanır.

---

## Import Job lifecycle

```
uploaded → sheet_selected → header_configured → mapping_completed
  → analysis_queued → analyzing → decision_required
  → applying → completed
```

| Status | Liste aksiyonu | Devam Et hedefi |
|--------|----------------|-----------------|
| `uploaded` | Devam Et | Sheet |
| `sheet_selected` | Devam Et | Header |
| `header_configured` | Devam Et | Mapping grid |
| `mapping_completed` | Analiz Yap | — |
| `decision_required` | Devam Et | Kararlar |
| `completed` | — | Liste |

---

## Resume davranışı

1. Upload sonrası kullanıcı **Import İşleri** listesine yönlendirilir (`onUploadComplete`).
2. **Devam Et** `/data-integration/imports/continue/:batchId` açar.
3. Wizard batch status'a göre setup veya decision modunu seçer.
4. Aynı batch'te dosya değiştirilemez; resume'da upload adımı salt okunur.
5. `GET /imports/{id}` artık `available_sheets`, `selected_sheet_name`, `header_mode`, `column_mapping_json` döner.

---

## Wizard değişiklikleri

- Yeni import: Fair → Upload → **liste** (wizard'da sheet'e otomatik geçiş yok).
- Resume setup: doğrudan sheet / header / mapping adımına atlama.
- Resume decision: Karar → Uygula → Özet akışı.

---

## Bulk Preview davranışı

1. Buton → `POST bulk-actions/preview`
2. Popup: `affected_rows` + `summary`
3. Onay yoksa hiçbir satır değişmez.

---

## Background Job davranışı

1. Onay → `POST bulk-actions/apply` → **202** + `job_id`
2. `ImportJobRunner.run_bulk_decision` kararları uygular
3. Sonuç: `processed_rows`, `skipped_rows`, `error_rows`
4. UI job poll + liste refresh
5. Apply job (`apply-job`) aynı batch'te eşzamanlı bulk/apply job varsa **409**

---

## Idempotency yaklaşımı

- `row_matches_bulk_action`: `row.decision is not None` ise satır atlanır.
- Aynı bulk action tekrar çalıştırıldığında yalnızca kararsız satırlar işlenir.
- Apply job lock: batch başına tek aktif `bulk_decision` veya `apply` job.

---

## Test sonuçları

| Suite | Sonuç |
|-------|-------|
| `pytest tests/modules/imports tests/modules/data_integration -q` | **90 PASS** |
| `npm run build` (frontend) | **PASS** |

---

## Bilinen limitler

- Background jobs hâlâ FastAPI `BackgroundTasks` (Redis/worker yok).
- Bulk job TestClient'ta ikinci istekle çakışma testi ayrı; tamamlanma polling UI'da.
- `mapping_completed` için Devam Et yok — yalnızca Analiz Yap.
- Mapping şablonları / Jobs / Reports sayfaları hâlâ placeholder.

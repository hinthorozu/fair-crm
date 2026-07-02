# Import Job Permanent Delete — Completion Report

**Date:** 2026-07-02

## Değişen dosyalar

### Backend
- `delete_import_batch.py` — **NEW** use case
- `import_repository.py` — `delete()` on batch repository
- `job_repository.py` — `has_any_active_job_for_batch()`
- `batch_status.py` — `has_active_batch_operation()`
- `exceptions.py` — `ImportBatchDeleteBlockedError`
- `routes.py` — `DELETE /{batch_id}`
- `test_delete_import_batch.py` — **NEW** (4 tests)

### Frontend
- `DataIntegrationImportsPage.tsx` — Sil + ConfirmDialog + toast
- `dataIntegration.ts` — `deleteImportBatch()`
- `dataIntegrationLabels.ts` — delete copy
- `styles.css` — toast + `pre-line` confirm message

## Cascade delete yaklaşımı

`crm_import_batches` satırı silindiğinde DB FK `ON DELETE CASCADE` ile otomatik kaldırılır:

- `crm_import_rows` (analyze, decision, raw/normalized JSON)
- `crm_import_jobs` (analyze/apply/bulk job kayıtları)

Batch kaydındaki `raw_preview_json`, `column_mapping_json` ve karar verileri row/batch ile birlikte gider.

## Fiziksel dosya silme yöntemi

Excel dosyası ayrı disk path'inde tutulmuyor; `stored_file_content` (BLOB) `crm_import_batches` üzerinde. Batch hard delete ile binary içerik de kalıcı olarak silinir.

## Transaction yaklaşımı

Tek HTTP isteği → `DeleteImportBatchUseCase` → aktif job/status kontrolü → `batch_repository.delete()` → `db.commit()`. Background job yok; sync transactional delete.

## Test sonuçları

| Suite | Sonuç |
|-------|-------|
| `pytest tests/modules/imports/test_delete_import_batch.py` | **4 PASS** |
| Full import suite | **94 PASS** |
| `npm run build` | **PASS** |

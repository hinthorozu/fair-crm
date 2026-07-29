import { dataIntegrationLabels } from "../labels/dataIntegrationLabels";
import type { ImportBatch } from "../types/import";

const LEGACY_ANALYZED_STATUSES = new Set([
  "decision_required",
  "analyzed",
  "previewed",
  "applying",
  "completed",
  "applied",
]);

export function hasImportBatchBeenAnalyzed(
  batch: Pick<ImportBatch, "analyzed_at" | "status">,
): boolean {
  if (batch.analyzed_at) return true;
  return LEGACY_ANALYZED_STATUSES.has(batch.status);
}

export function importAnalysisStatusLabel(
  batch: Pick<ImportBatch, "analyzed_at" | "status">,
): string {
  return hasImportBatchBeenAnalyzed(batch)
    ? dataIntegrationLabels.analysisStatusAnalyzed
    : dataIntegrationLabels.analysisStatusNotAnalyzed;
}

export function formatImportLastAnalyzedAt(analyzedAt: string | null | undefined): string {
  if (!analyzedAt) return "—";
  return new Date(analyzedAt).toLocaleString("tr-TR");
}

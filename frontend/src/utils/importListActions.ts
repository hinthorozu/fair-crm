import { canResumeDecisions, canResumeSetup } from "./importResume";

export function canAnalyzeImportBatch(status: string): boolean {
  return status === "mapping_completed" || status === "mapped" || status === "analysis_failed";
}

export function isImportBatchOperationInProgress(status: string): boolean {
  return (
    status === "analyzing" ||
    status === "analysis_queued" ||
    status === "applying"
  );
}

export function showContinueImportBatch(status: string): boolean {
  if (isImportBatchOperationInProgress(status)) return false;
  return canResumeSetup(status) || canResumeDecisions(status);
}

/** Labels for primary list actions (excluding delete). */
export function importBatchListPrimaryActions(status: string): string[] {
  const actions: string[] = [];
  if (canAnalyzeImportBatch(status)) {
    actions.push("analyze");
  }
  if (isImportBatchOperationInProgress(status)) {
    actions.push("in_progress");
  }
  if (showContinueImportBatch(status)) {
    actions.push("continue");
  }
  return actions;
}

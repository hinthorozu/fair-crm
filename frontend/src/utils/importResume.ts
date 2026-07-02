import type { ImportBatchStatus } from "../types/import";
import { WIZARD_SETUP_STEPS } from "../labels/importLabels";

const SETUP_RESUME_STATUSES: ImportBatchStatus[] = [
  "uploaded",
  "sheet_selected",
  "header_configured",
];

const DECISION_RESUME_STATUSES: ImportBatchStatus[] = [
  "analyzed",
  "decision_required",
  "applying",
];

export function canResumeSetup(status: ImportBatchStatus | string): boolean {
  return SETUP_RESUME_STATUSES.includes(status as ImportBatchStatus);
}

export function canResumeDecisions(status: ImportBatchStatus | string): boolean {
  return DECISION_RESUME_STATUSES.includes(status as ImportBatchStatus);
}

export function setupStepIndexForStatus(status: ImportBatchStatus | string): number {
  const stepId =
    status === "uploaded"
      ? "sheet"
      : status === "sheet_selected"
        ? "header"
        : status === "header_configured"
          ? "mapping"
          : null;
  if (!stepId) return 0;
  const index = WIZARD_SETUP_STEPS.findIndex((s) => s.id === stepId);
  return index >= 0 ? index : 0;
}

export function isTerminalBatchStatus(status: ImportBatchStatus | string): boolean {
  return status === "completed" || status === "failed" || status === "cancelled" || status === "applied";
}

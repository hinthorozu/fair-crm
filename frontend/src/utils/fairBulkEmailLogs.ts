import type { BadgeVariant } from "../components/ui/Badge";
import { fairLabels } from "../labels/fairLabels";

const ACTIVE_BATCH_STATUSES = new Set(["queued", "processing"]);

export function isActiveBatchStatus(status: string): boolean {
  return ACTIVE_BATCH_STATUSES.has(status);
}

export function fairEmailBatchStatusLabel(status: string): string {
  return fairLabels.bulkEmailBatchStatusLabels[status] ?? status;
}

export function fairEmailBatchStatusVariant(status: string): BadgeVariant {
  switch (status) {
    case "completed":
      return "success";
    case "processing":
      return "info";
    case "queued":
      return "neutral";
    case "failed":
      return "danger";
    case "completed_with_errors":
    case "partial_failed":
      return "warning";
    default:
      return "default";
  }
}

export function fairEmailOutboxStatusLabel(status: string): string {
  return fairLabels.bulkEmailOutboxStatusLabels[status] ?? status;
}

export function fairEmailOutboxStatusVariant(status: string): BadgeVariant {
  switch (status) {
    case "sent":
      return "success";
    case "failed":
      return "danger";
    case "queued":
    case "pending":
      return "neutral";
    case "sending":
      return "info";
    case "skipped":
      return "warning";
    default:
      return "default";
  }
}

export function formatFairEmailDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

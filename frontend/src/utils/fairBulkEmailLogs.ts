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

export function fairEmailDeliveryStatusLabel(status: string, providerStatus?: string | null): string {
  switch ((providerStatus ?? "").trim()) {
    case "accepted":
    case "sent":
      return "Kabul edildi";
    case "delivered":
    case "opened":
    case "clicked":
      return "Teslim edildi";
    case "deferred":
      return "Gecikmeli";
    case "soft_bounced":
    case "hard_bounced":
    case "suppressed":
      return "Teslim edilemedi";
    case "unsubscribed":
      return "Abonelikten çıktı";
    case "spam_complaint":
      return "Spam bildirimi";
    default:
      return fairEmailOutboxStatusLabel(status);
  }
}

export function fairEmailDeliveryStatusVariant(
  status: string,
  providerStatus?: string | null,
): BadgeVariant {
  switch ((providerStatus ?? "").trim()) {
    case "delivered":
    case "opened":
    case "clicked":
      return "success";
    case "accepted":
    case "sent":
      return "info";
    case "deferred":
      return "warning";
    case "soft_bounced":
    case "hard_bounced":
    case "suppressed":
    case "unsubscribed":
    case "spam_complaint":
      return "danger";
    default:
      return fairEmailOutboxStatusVariant(status);
  }
}

export function formatFairEmailDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

import type { BadgeVariant } from "../components/ui/Badge";
import type { ScraperRunStatus } from "../types/scraper";
import { scraperLabels } from "../labels/scraperLabels";

export function runStatusBadgeVariant(status: ScraperRunStatus | string): BadgeVariant {
  if (status === "running") return "info";
  if (status === "cancel_requested" || status === "cancelling") return "warning";
  if (status === "completed") return "success";
  if (status === "failed") return "danger";
  if (status === "cancelled") return "neutral";
  return "default";
}

export function runStatusLabel(status: ScraperRunStatus | string): string {
  if (status === "running") return scraperLabels.runStatusRunning;
  if (status === "cancel_requested" || status === "cancelling") return scraperLabels.runStatusCancelRequested;
  if (status === "completed") return scraperLabels.runStatusCompleted;
  if (status === "failed") return scraperLabels.runStatusFailed;
  if (status === "cancelled") return scraperLabels.runStatusCancelled;
  return status;
}

export function isActiveScraperRunStatus(status: ScraperRunStatus | string): boolean {
  return status === "running" || status === "cancel_requested" || status === "cancelling";
}

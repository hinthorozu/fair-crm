import type { BadgeVariant } from "../components/ui/Badge";
import type { AdapterStatus, ScraperRunStatus } from "../types/scraper";
import { scraperLabels } from "../labels/scraperLabels";

export function adapterStatusBadgeVariant(status: string): BadgeVariant {
  if (status === "stable") return "success";
  if (status === "experimental") return "warning";
  if (status === "deprecated") return "neutral";
  return "default";
}

export function adapterStatusLabel(status: string): string {
  if (status === "stable") return scraperLabels.statusStable;
  if (status === "experimental") return scraperLabels.statusExperimental;
  if (status === "deprecated") return scraperLabels.statusDeprecated;
  return status;
}

export function runStatusBadgeVariant(status: ScraperRunStatus | string): BadgeVariant {
  if (status === "running") return "info";
  if (status === "completed") return "success";
  if (status === "failed") return "danger";
  return "default";
}

export function runStatusLabel(status: ScraperRunStatus | string): string {
  if (status === "running") return scraperLabels.runStatusRunning;
  if (status === "completed") return scraperLabels.runStatusCompleted;
  if (status === "failed") return scraperLabels.runStatusFailed;
  return status;
}

export function formatAdapterStatusFilter(status: AdapterStatus): string {
  if (status === "stable") return scraperLabels.filterStatusStable;
  if (status === "experimental") return scraperLabels.filterStatusExperimental;
  return scraperLabels.filterStatusDeprecated;
}

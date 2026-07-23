import type { BadgeVariant } from "../components/ui/Badge";
import type { ScraperRunStatus } from "../types/scraper";
import {
  mapTechnicalRunStatusToUserFacing,
  operationUserFacingStatusBadgeVariant,
  operationUserFacingStatusLabel,
} from "./operationRunStatus";

/**
 * Map scraper-history technical statuses onto Operation Engine technical statuses
 * before applying the shared user-facing mapping.
 *
 * cancel_requested / cancelling are scraper-internal transitions; OperationRun
 * treats them as running — do the same here (no scraper-only Turkish labels).
 */
function toOperationTechnicalStatus(status: ScraperRunStatus | string): string {
  const normalized = String(status).trim().toLowerCase();
  if (normalized === "cancel_requested" || normalized === "cancelling") {
    return "running";
  }
  return normalized;
}

/** Shared Operation Engine badge variant for scraper run statuses. */
export function runStatusBadgeVariant(status: ScraperRunStatus | string): BadgeVariant {
  const userFacing = mapTechnicalRunStatusToUserFacing(toOperationTechnicalStatus(status));
  if (userFacing) return operationUserFacingStatusBadgeVariant(userFacing);
  return "default";
}

/** Shared Operation Engine user-facing label for scraper run statuses. */
export function runStatusLabel(status: ScraperRunStatus | string): string {
  const userFacing = mapTechnicalRunStatusToUserFacing(toOperationTechnicalStatus(status));
  if (userFacing) return operationUserFacingStatusLabel(userFacing);
  return String(status);
}

export function isActiveScraperRunStatus(status: ScraperRunStatus | string): boolean {
  return status === "running" || status === "cancel_requested" || status === "cancelling";
}

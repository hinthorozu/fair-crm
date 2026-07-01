import type { ImportRowStatus, MergeOutcome } from "../types/import";
import type { BadgeVariant } from "../components/ui/Badge";

export function mergeOutcomeBadgeVariant(outcome: MergeOutcome | string): BadgeVariant {
  const map: Record<string, BadgeVariant> = {
    same: "neutral",
    new: "info",
    will_add: "success",
    will_update: "primary",
    will_keep: "warning",
    conflict: "danger",
    empty: "neutral",
    skipped: "neutral",
  };
  return map[outcome] ?? "neutral";
}

export function importRowStatusBadgeVariant(status: ImportRowStatus | string): BadgeVariant {
  const map: Record<string, BadgeVariant> = {
    pending: "neutral",
    valid: "success",
    invalid: "danger",
    possible_duplicate: "warning",
    ready_to_create: "info",
    ready_to_update: "primary",
    applied: "success",
    skipped: "neutral",
  };
  return map[status] ?? "neutral";
}

export function importBatchStatusBadgeVariant(status: string): BadgeVariant {
  const map: Record<string, BadgeVariant> = {
    uploaded: "neutral",
    mapped: "info",
    analyzed: "info",
    previewed: "info",
    applied: "success",
    failed: "danger",
    cancelled: "neutral",
  };
  return map[status] ?? "neutral";
}

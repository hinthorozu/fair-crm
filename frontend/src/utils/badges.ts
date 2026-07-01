import type { ActivitySource, ActivityStatus, ActivityType } from "../types/activity";
import type { BadgeVariant } from "../components/ui/Badge";

export function activityTypeBadgeVariant(type: ActivityType): BadgeVariant {
  const map: Record<ActivityType, BadgeVariant> = {
    call: "primary",
    meeting: "info",
    email: "neutral",
    whatsapp: "success",
    note: "warning",
    fair_visit: "primary",
    follow_up: "info",
    other: "neutral",
  };
  return map[type] ?? "neutral";
}

export function activityStatusBadgeVariant(status: ActivityStatus): BadgeVariant {
  const map: Record<ActivityStatus, BadgeVariant> = {
    open: "warning",
    completed: "success",
    cancelled: "danger",
  };
  return map[status] ?? "neutral";
}

export function activitySourceBadgeVariant(source: ActivitySource): BadgeVariant {
  const map: Record<ActivitySource, BadgeVariant> = {
    manual: "neutral",
    system: "info",
    email_automation: "primary",
    whatsapp_integration: "success",
    import: "warning",
    other: "neutral",
  };
  return map[source] ?? "neutral";
}

export function customerStatusBadgeVariant(status: string): BadgeVariant {
  const map: Record<string, BadgeVariant> = {
    lead: "warning",
    active: "success",
    inactive: "neutral",
    archived: "danger",
  };
  return map[status] ?? "neutral";
}

export function participationStatusBadgeVariant(status: string): BadgeVariant {
  const map: Record<string, BadgeVariant> = {
    planned: "info",
    exhibitor: "primary",
    visited: "success",
    contacted: "warning",
    follow_up_required: "warning",
    not_interested: "danger",
    customer: "success",
    other: "neutral",
  };
  return map[status] ?? "neutral";
}

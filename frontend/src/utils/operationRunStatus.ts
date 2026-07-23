import type { BadgeVariant } from "../components/ui/Badge";
import type { Operation, OperationRun } from "../types/operation";

/**
 * Canonical user-facing Operation Engine run statuses.
 * Shared across all automation types — do not add type-specific variants.
 */
export type OperationUserFacingStatus =
  | "scheduled"
  | "running"
  | "paused"
  | "completed"
  | "cancelled"
  | "failed";

export const OPERATION_USER_FACING_STATUSES: readonly OperationUserFacingStatus[] = [
  "scheduled",
  "running",
  "paused",
  "completed",
  "cancelled",
  "failed",
] as const;

export const operationUserFacingStatusLabels: Record<OperationUserFacingStatus, string> = {
  scheduled: "Zamanlandı",
  running: "Çalışıyor",
  paused: "Durduruldu",
  completed: "Bitti",
  cancelled: "İptal",
  failed: "Hata",
};

function parseFutureSchedule(runSettings?: Record<string, unknown> | null): boolean {
  if (!runSettings) return false;
  const raw = runSettings.schedule ?? runSettings.scheduled_at ?? runSettings.run_at;
  if (typeof raw !== "string" || !raw.trim()) return false;
  const ts = Date.parse(raw.trim());
  if (!Number.isFinite(ts)) return false;
  return ts > Date.now();
}

/**
 * Map technical OperationRun status → user-facing status.
 *
 * `queued` is NOT automatically Zamanlandı. Immediate worker-queue waits map to
 * Çalışıyor. Only a real future schedule (or technical `scheduled`) → Zamanlandı.
 */
export function mapTechnicalRunStatusToUserFacing(
  technicalStatus: string | null | undefined,
  options?: { runSettings?: Record<string, unknown> | null },
): OperationUserFacingStatus | null {
  if (!technicalStatus) return null;
  const status = technicalStatus.trim().toLowerCase();
  if (!status) return null;

  switch (status) {
    case "scheduled":
      return "scheduled";
    case "queued":
      return parseFutureSchedule(options?.runSettings) ? "scheduled" : "running";
    case "running":
      return "running";
    case "paused":
      return "paused";
    case "completed":
      return "completed";
    case "cancelled":
      return "cancelled";
    case "failed":
      return "failed";
    default:
      return null;
  }
}

export function operationUserFacingStatusBadgeVariant(
  status: OperationUserFacingStatus,
): BadgeVariant {
  switch (status) {
    case "scheduled":
      return "warning";
    case "running":
      return "info";
    case "paused":
      return "warning";
    case "completed":
      return "success";
    case "cancelled":
      return "neutral";
    case "failed":
      return "danger";
    default:
      return "neutral";
  }
}

export function operationUserFacingStatusLabel(
  status: OperationUserFacingStatus | null | undefined,
): string {
  if (!status) return "—";
  return operationUserFacingStatusLabels[status] ?? status;
}

/** Resolve user-facing status from an OperationRun (+ optional operation run_settings). */
export function resolveRunUserFacingStatus(
  run: Pick<OperationRun, "status"> | null | undefined,
  runSettings?: Record<string, unknown> | null,
): OperationUserFacingStatus | null {
  if (!run) return null;
  return mapTechnicalRunStatusToUserFacing(run.status, { runSettings });
}

/** Resolve user-facing status for an Operation via its latest_run. */
export function resolveOperationUserFacingStatus(
  operation: Pick<Operation, "latest_run" | "run_settings"> | null | undefined,
): OperationUserFacingStatus | null {
  if (!operation?.latest_run) return null;
  return mapTechnicalRunStatusToUserFacing(operation.latest_run.status, {
    runSettings: operation.run_settings,
  });
}

/** Values sent as list `status` filter (user-facing keys). */
export function operationUserFacingStatusFilterOptions(): {
  value: OperationUserFacingStatus;
  label: string;
}[] {
  return OPERATION_USER_FACING_STATUSES.map((value) => ({
    value,
    label: operationUserFacingStatusLabels[value],
  }));
}

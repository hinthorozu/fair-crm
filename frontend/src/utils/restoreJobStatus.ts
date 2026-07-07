import type { SystemBackupRestoreJobResponse } from "../types/systemBackup";

export type RestoreJobApiStatus = SystemBackupRestoreJobResponse["status"];

export const RESTORE_JOB_POLL_INTERVAL_MS = 2500;

export function isTerminalRestoreJobStatus(status: RestoreJobApiStatus): boolean {
  return status === "completed" || status === "failed";
}

export function shouldPollRestoreJobStatus(status: RestoreJobApiStatus): boolean {
  return !isTerminalRestoreJobStatus(status);
}

export type RestoreJobUiStatus = "queued" | "running" | "succeeded" | "failed";

export function mapRestoreJobUiStatus(status: RestoreJobApiStatus): RestoreJobUiStatus {
  if (status === "manual_restore_required") return "queued";
  if (status === "running") return "running";
  if (status === "completed") return "succeeded";
  return "failed";
}

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SystemBackupRestoreJobResponse } from "../types/systemBackup";
import { RestoreJobPoller } from "./restoreJobPoller";
import { RESTORE_JOB_POLL_INTERVAL_MS } from "./restoreJobStatus";

function makeJob(
  overrides: Partial<SystemBackupRestoreJobResponse> & Pick<SystemBackupRestoreJobResponse, "id" | "status">,
): SystemBackupRestoreJobResponse {
  return {
    source_type: "existing_backup",
    source_database_key: "fair_crm",
    target_database_key: "fair_crm",
    backup_id: "00000000-0000-4000-8000-000000000001",
    source_file_name: "fair_crm_backup_test.dump",
    checksum_sha256: null,
    notes: null,
    requested_by_user_id: "00000000-0000-4000-8000-000000000002",
    requested_by_email: "dev@example.com",
    requested_at: "2026-07-07T10:00:00.000Z",
    started_at: null,
    completed_at: null,
    failed_at: null,
    error_message: null,
    restore_log_path: null,
    message: "test",
    uploaded: false,
    backup_file_name: "fair_crm_backup_test.dump",
    backup_format: "postgresql_dump",
    ...overrides,
  };
}

describe("RestoreJobPoller", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("polls queued → running → succeeded and stops on terminal status", async () => {
    const jobId = "00000000-0000-4000-8000-000000000099";
    const responses = [
      makeJob({ id: jobId, status: "manual_restore_required" }),
      makeJob({ id: jobId, status: "running", started_at: "2026-07-07T10:00:01.000Z" }),
      makeJob({
        id: jobId,
        status: "completed",
        started_at: "2026-07-07T10:00:01.000Z",
        completed_at: "2026-07-07T10:00:05.000Z",
        restore_log_path: "data/restore_logs/job.log",
      }),
    ];
    const fetchJob = vi.fn(async () => responses.shift() ?? responses[responses.length - 1]);
    const onUpdate = vi.fn();
    const onTerminal = vi.fn();

    const poller = new RestoreJobPoller({ fetchJob, onUpdate, onTerminal });
    poller.track(jobId);

    await Promise.resolve();
    expect(fetchJob).toHaveBeenCalledTimes(1);
    expect(onUpdate).toHaveBeenCalledWith(expect.objectContaining({ status: "manual_restore_required" }));

    await vi.advanceTimersByTimeAsync(RESTORE_JOB_POLL_INTERVAL_MS);
    expect(fetchJob).toHaveBeenCalledTimes(2);
    expect(onUpdate).toHaveBeenCalledWith(expect.objectContaining({ status: "running" }));

    await vi.advanceTimersByTimeAsync(RESTORE_JOB_POLL_INTERVAL_MS);
    expect(fetchJob).toHaveBeenCalledTimes(3);
    expect(onTerminal).toHaveBeenCalledWith(expect.objectContaining({ status: "completed" }));
    expect(poller.getTrackedJobIds()).toEqual([]);

    await vi.advanceTimersByTimeAsync(RESTORE_JOB_POLL_INTERVAL_MS * 2);
    expect(fetchJob).toHaveBeenCalledTimes(3);

    poller.dispose();
  });

  it("polls until failed and exposes error_message", async () => {
    const jobId = "00000000-0000-4000-8000-000000000088";
    const fetchJob = vi
      .fn()
      .mockResolvedValueOnce(makeJob({ id: jobId, status: "running", started_at: "2026-07-07T10:00:01.000Z" }))
      .mockResolvedValueOnce(
        makeJob({
          id: jobId,
          status: "failed",
          failed_at: "2026-07-07T10:00:03.000Z",
          error_message: "pg_restore failed",
        }),
      );
    const onTerminal = vi.fn();
    const poller = new RestoreJobPoller({ fetchJob, onTerminal });

    poller.track(jobId);
    await Promise.resolve();
    await vi.advanceTimersByTimeAsync(RESTORE_JOB_POLL_INTERVAL_MS);

    expect(onTerminal).toHaveBeenCalledWith(
      expect.objectContaining({ status: "failed", error_message: "pg_restore failed" }),
    );
    expect(poller.getTrackedJobIds()).toEqual([]);
    poller.dispose();
  });

  it("dispose clears polling interval and stops further fetches (hook unmount cleanup)", async () => {
    const jobId = "00000000-0000-4000-8000-000000000077";
    const fetchJob = vi.fn(async () => makeJob({ id: jobId, status: "manual_restore_required" }));
    const poller = new RestoreJobPoller({ fetchJob });

    poller.track(jobId);
    await Promise.resolve();
    expect(fetchJob).toHaveBeenCalledTimes(1);

    poller.dispose();
    await vi.advanceTimersByTimeAsync(RESTORE_JOB_POLL_INTERVAL_MS * 3);
    expect(fetchJob).toHaveBeenCalledTimes(1);
  });
});

describe("restoreJobStatus helpers", () => {
  it("maps API statuses to UI statuses", async () => {
    const { mapRestoreJobUiStatus, isTerminalRestoreJobStatus } = await import("./restoreJobStatus");
    expect(mapRestoreJobUiStatus("manual_restore_required")).toBe("queued");
    expect(mapRestoreJobUiStatus("running")).toBe("running");
    expect(mapRestoreJobUiStatus("completed")).toBe("succeeded");
    expect(mapRestoreJobUiStatus("failed")).toBe("failed");
    expect(isTerminalRestoreJobStatus("completed")).toBe(true);
    expect(isTerminalRestoreJobStatus("failed")).toBe(true);
    expect(isTerminalRestoreJobStatus("running")).toBe(false);
  });
});

import type { SystemBackupRestoreJobResponse } from "../types/systemBackup";
import {
  RESTORE_JOB_POLL_INTERVAL_MS,
  isTerminalRestoreJobStatus,
  shouldPollRestoreJobStatus,
} from "./restoreJobStatus";

export interface RestoreJobPollerOptions {
  fetchJob: (jobId: string) => Promise<SystemBackupRestoreJobResponse>;
  intervalMs?: number;
  onUpdate?: (job: SystemBackupRestoreJobResponse) => void;
  onTerminal?: (job: SystemBackupRestoreJobResponse) => void;
  onError?: (error: unknown, jobId: string) => void;
}

export class RestoreJobPoller {
  private readonly fetchJob: RestoreJobPollerOptions["fetchJob"];
  private readonly intervalMs: number;
  private readonly onUpdate?: RestoreJobPollerOptions["onUpdate"];
  private readonly onTerminal?: RestoreJobPollerOptions["onTerminal"];
  private readonly onError?: RestoreJobPollerOptions["onError"];
  private readonly trackedIds = new Set<string>();
  private timer: ReturnType<typeof setInterval> | null = null;
  private disposed = false;

  constructor(options: RestoreJobPollerOptions) {
    this.fetchJob = options.fetchJob;
    this.intervalMs = options.intervalMs ?? RESTORE_JOB_POLL_INTERVAL_MS;
    this.onUpdate = options.onUpdate;
    this.onTerminal = options.onTerminal;
    this.onError = options.onError;
  }

  track(jobId: string, job?: SystemBackupRestoreJobResponse): void {
    if (this.disposed || !jobId) return;
    if (job && isTerminalRestoreJobStatus(job.status)) {
      this.onUpdate?.(job);
      this.onTerminal?.(job);
      return;
    }
    this.trackedIds.add(jobId);
    if (job) {
      this.onUpdate?.(job);
    }
    this.ensureTimer();
    void this.pollOnce(jobId);
  }

  untrack(jobId: string): void {
    this.trackedIds.delete(jobId);
    if (this.trackedIds.size === 0) {
      this.clearTimer();
    }
  }

  dispose(): void {
    this.disposed = true;
    this.trackedIds.clear();
    this.clearTimer();
  }

  getTrackedJobIds(): string[] {
    return [...this.trackedIds];
  }

  private ensureTimer(): void {
    if (this.timer != null || this.disposed) return;
    this.timer = setInterval(() => {
      void this.pollAll();
    }, this.intervalMs);
  }

  private clearTimer(): void {
    if (this.timer == null) return;
    clearInterval(this.timer);
    this.timer = null;
  }

  private async pollAll(): Promise<void> {
    for (const jobId of [...this.trackedIds]) {
      await this.pollOnce(jobId);
    }
  }

  private async pollOnce(jobId: string): Promise<void> {
    if (this.disposed || !this.trackedIds.has(jobId)) return;
    try {
      const job = await this.fetchJob(jobId);
      this.onUpdate?.(job);
      if (isTerminalRestoreJobStatus(job.status)) {
        this.untrack(jobId);
        this.onTerminal?.(job);
        return;
      }
      if (!shouldPollRestoreJobStatus(job.status)) {
        this.untrack(jobId);
      }
    } catch (error) {
      this.onError?.(error, jobId);
    }
  }
}

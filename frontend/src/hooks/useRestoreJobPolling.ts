import React from "react";
import { getRestoreJob } from "../api/systemAdmin";
import type { SystemBackupRestoreJobResponse } from "../types/systemBackup";
import { RestoreJobPoller } from "../utils/restoreJobPoller";
import { shouldPollRestoreJobStatus } from "../utils/restoreJobStatus";

export interface UseRestoreJobPollingOptions {
  onTerminal?: (job: SystemBackupRestoreJobResponse) => void;
}

export function useRestoreJobPolling(options: UseRestoreJobPollingOptions = {}) {
  const onTerminalRef = React.useRef(options.onTerminal);
  onTerminalRef.current = options.onTerminal;

  const [trackedJobs, setTrackedJobs] = React.useState<Map<string, SystemBackupRestoreJobResponse>>(
    () => new Map(),
  );
  const pollerRef = React.useRef<RestoreJobPoller | null>(null);

  React.useEffect(() => {
    const poller = new RestoreJobPoller({
      fetchJob: getRestoreJob,
      onUpdate: (job) => {
        setTrackedJobs((prev) => {
          const next = new Map(prev);
          next.set(job.id, job);
          return next;
        });
      },
      onTerminal: (job) => {
        setTrackedJobs((prev) => {
          const next = new Map(prev);
          next.set(job.id, job);
          return next;
        });
        onTerminalRef.current?.(job);
      },
    });
    pollerRef.current = poller;
    return () => {
      poller.dispose();
      pollerRef.current = null;
    };
  }, []);

  const trackRestoreJob = React.useCallback((job: SystemBackupRestoreJobResponse) => {
    pollerRef.current?.track(job.id, job);
  }, []);

  const syncRestoreJobsFromList = React.useCallback((jobs: SystemBackupRestoreJobResponse[]) => {
    for (const job of jobs) {
      if (shouldPollRestoreJobStatus(job.status)) {
        pollerRef.current?.track(job.id, job);
      }
    }
  }, []);

  return {
    trackedJobs,
    trackRestoreJob,
    syncRestoreJobsFromList,
  };
}

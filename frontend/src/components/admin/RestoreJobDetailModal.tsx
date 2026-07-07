import React from "react";
import { getRestoreJob, getRestoreJobLog } from "../../api/systemAdmin";
import { adminLabels } from "../../labels/adminLabels";
import type { SystemBackupRestoreJobResponse } from "../../types/systemBackup";
import {
  RESTORE_JOB_POLL_INTERVAL_MS,
  isTerminalRestoreJobStatus,
  mapRestoreJobUiStatus,
  shouldPollRestoreJobStatus,
} from "../../utils/restoreJobStatus";
import { Badge } from "../ui/Badge";
import { Modal } from "../ui/Modal";
import type { BadgeVariant } from "../ui/Badge";

function restoreJobStatusBadgeVariant(status: SystemBackupRestoreJobResponse["status"]): BadgeVariant {
  const uiStatus = mapRestoreJobUiStatus(status);
  if (uiStatus === "queued") return "warning";
  if (uiStatus === "running") return "info";
  if (uiStatus === "succeeded") return "success";
  return "danger";
}

function restoreJobStatusLabel(status: SystemBackupRestoreJobResponse["status"]): string {
  const uiStatus = mapRestoreJobUiStatus(status);
  if (uiStatus === "queued") return adminLabels.restoreJobStatusQueued;
  if (uiStatus === "running") return adminLabels.restoreJobStatusRunning;
  if (uiStatus === "succeeded") return adminLabels.restoreJobStatusSucceeded;
  return adminLabels.restoreJobStatusFailed;
}

function restoreJobSourceLabel(sourceType: SystemBackupRestoreJobResponse["source_type"]): string {
  return sourceType === "existing_backup"
    ? adminLabels.restoreJobSourceExisting
    : adminLabels.restoreJobSourceUpload;
}

function databaseKeyLabel(key: SystemBackupRestoreJobResponse["source_database_key"]): string {
  return key === "kyrox_core" ? adminLabels.databaseKeyKyroxCore : adminLabels.databaseKeyFairCrm;
}

function restoreJobFileLabel(job: SystemBackupRestoreJobResponse): string {
  if (job.backup_file_name) {
    return job.backup_file_name;
  }
  return job.source_file_name;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

function buildRunnerCommand(jobId: string): string {
  return `$env:ALLOW_RESTORE = "true"\n.\\scripts\\dev\\run-restore-job.ps1 -RestoreJobId "${jobId}"\n\n# sunucu:\nALLOW_RESTORE=true bash scripts/server/run-restore-job.sh ${jobId}`;
}

type RestoreJobDetailModalProps = {
  job: SystemBackupRestoreJobResponse;
  onClose: () => void;
  onJobUpdated?: (job: SystemBackupRestoreJobResponse) => void;
};

export function RestoreJobDetailModal({ job, onClose, onJobUpdated }: RestoreJobDetailModalProps) {
  const [liveJob, setLiveJob] = React.useState(job);
  const [logContent, setLogContent] = React.useState("");
  const [logExists, setLogExists] = React.useState(false);
  const [logTruncated, setLogTruncated] = React.useState(false);
  const [logLoading, setLogLoading] = React.useState(true);
  const logRef = React.useRef<HTMLPreElement | null>(null);

  const refreshDetail = React.useCallback(async () => {
    const [freshJob, freshLog] = await Promise.all([
      getRestoreJob(job.id),
      getRestoreJobLog(job.id),
    ]);
    setLiveJob(freshJob);
    onJobUpdated?.(freshJob);
    setLogExists(freshLog.exists);
    setLogTruncated(freshLog.truncated);
    setLogContent(freshLog.exists ? freshLog.content : "");
    setLogLoading(false);
  }, [job.id, onJobUpdated]);

  React.useEffect(() => {
    setLiveJob(job);
  }, [job]);

  React.useEffect(() => {
    let cancelled = false;
    setLogLoading(true);

    const load = async () => {
      try {
        if (cancelled) return;
        await refreshDetail();
      } catch {
        if (!cancelled) {
          setLogLoading(false);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [refreshDetail]);

  React.useEffect(() => {
    if (!shouldPollRestoreJobStatus(liveJob.status)) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      void refreshDetail();
    }, RESTORE_JOB_POLL_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [liveJob.status, refreshDetail]);

  React.useEffect(() => {
    const node = logRef.current;
    if (!node) return;
    node.scrollTop = node.scrollHeight;
  }, [logContent]);

  const uiStatus = mapRestoreJobUiStatus(liveJob.status);
  const showLogPlaceholder = !logLoading && !logExists;
  const runnerCommand = buildRunnerCommand(liveJob.id);

  return (
    <Modal title={adminLabels.restoreJobDetailsTitle} onClose={onClose} size="lg">
      {liveJob.error_message && (
        <div className="restore-job-detail-error" role="alert">
          {liveJob.error_message}
        </div>
      )}

      <dl className="detail-list restore-job-detail-list">
        <dt>{adminLabels.restoreJobColStatus}</dt>
        <dd>
          <Badge variant={restoreJobStatusBadgeVariant(liveJob.status)}>
            {restoreJobStatusLabel(liveJob.status)}
          </Badge>
        </dd>
        <dt>{adminLabels.restoreJobColSourceDatabase}</dt>
        <dd>{databaseKeyLabel(liveJob.source_database_key)}</dd>
        <dt>{adminLabels.restoreJobColTargetDatabase}</dt>
        <dd>{databaseKeyLabel(liveJob.target_database_key)}</dd>
        <dt>{adminLabels.restoreJobColFile}</dt>
        <dd>{restoreJobFileLabel(liveJob)}</dd>
        <dt>{adminLabels.restoreJobColSource}</dt>
        <dd>{restoreJobSourceLabel(liveJob.source_type)}</dd>
        <dt>{adminLabels.restoreJobColRequestedAt}</dt>
        <dd>{formatDateTime(liveJob.requested_at)}</dd>
        <dt>{adminLabels.restoreJobDetailStartedAt}</dt>
        <dd>{formatDateTime(liveJob.started_at)}</dd>
        <dt>{adminLabels.restoreJobDetailCompletedAt}</dt>
        <dd>{formatDateTime(liveJob.completed_at ?? liveJob.failed_at)}</dd>
        <dt>{adminLabels.restoreJobDetailLogPath}</dt>
        <dd className="mono">{liveJob.restore_log_path ?? "—"}</dd>
        <dt>{adminLabels.restoreJobDetailRunnerCommand}</dt>
        <dd className="mono restore-job-runner-command">{runnerCommand}</dd>
      </dl>

      {uiStatus === "queued" && (
        <p className="text-muted backup-restore-manual-hint">{adminLabels.restoreJobManualHint}</p>
      )}

      <div className="restore-job-live-log-section">
        <div className="restore-job-live-log-header">
          <h3>{adminLabels.restoreJobLiveLogTitle}</h3>
          {shouldPollRestoreJobStatus(liveJob.status) && (
            <span className="restore-job-live-log-polling">{adminLabels.restoreJobLiveLogPolling}</span>
          )}
        </div>
        {logTruncated && (
          <p className="text-muted restore-job-live-log-truncated">{adminLabels.restoreJobLiveLogTruncated}</p>
        )}
        {logLoading ? (
          <p className="text-muted">{adminLabels.restoreJobLiveLogLoading}</p>
        ) : showLogPlaceholder ? (
          <p className="text-muted">{adminLabels.restoreJobLiveLogMissing}</p>
        ) : (
          <pre ref={logRef} className="restore-job-live-log">
            {logContent || adminLabels.restoreJobLiveLogEmpty}
          </pre>
        )}
      </div>
    </Modal>
  );
}

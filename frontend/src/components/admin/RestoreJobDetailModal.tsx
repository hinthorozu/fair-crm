import React from "react";
import { deleteRestoreJob, getRestoreJob, getRestoreJobLog, startRestoreJob } from "../../api/systemAdmin";
import { adminLabels } from "../../labels/adminLabels";
import {
  canCreateAdminBackupOperation,
  canDeleteAdminBackupOperation,
} from "../../permissions/adminBackupPermissions";
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


type RestoreJobDetailModalProps = {
  job: SystemBackupRestoreJobResponse;
  onClose: () => void;
  onJobUpdated?: (job: SystemBackupRestoreJobResponse) => void;
  onDeleted?: () => void;
};

export function RestoreJobDetailModal({ job, onClose, onJobUpdated, onDeleted }: RestoreJobDetailModalProps) {
  const canStart = React.useMemo(() => canCreateAdminBackupOperation(), []);
  const canDelete = React.useMemo(() => canDeleteAdminBackupOperation(), []);
  const [liveJob, setLiveJob] = React.useState(job);
  const [logContent, setLogContent] = React.useState("");
  const [logExists, setLogExists] = React.useState(false);
  const [logTruncated, setLogTruncated] = React.useState(false);
  const [logLoading, setLogLoading] = React.useState(true);
  const [starting, setStarting] = React.useState(false);
  const [startError, setStartError] = React.useState("");
  const [startMessage, setStartMessage] = React.useState("");
  const [deleting, setDeleting] = React.useState(false);
  const [deleteError, setDeleteError] = React.useState("");
  const logRef = React.useRef<HTMLPreElement | null>(null);
  const onJobUpdatedRef = React.useRef(onJobUpdated);

  React.useEffect(() => {
    onJobUpdatedRef.current = onJobUpdated;
  }, [onJobUpdated]);

  const refreshDetail = React.useCallback(async () => {
    const jobRequest = getRestoreJob(job.id).then((freshJob) => {
      setLiveJob(freshJob);
      onJobUpdatedRef.current?.(freshJob);
    });
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 8000);
    try {
      const freshLog = await getRestoreJobLog(job.id, controller.signal);
      setLogExists(freshLog.exists);
      setLogTruncated(freshLog.truncated);
      setLogContent(freshLog.exists ? freshLog.content : "");
    } catch {
      // A transient polling error must not blank a log that is already visible.
    } finally {
      window.clearTimeout(timeout);
      setLogLoading(false);
    }
    await jobRequest;
  }, [job.id]);

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

  const handleStart = async () => {
    if (!canStart) return;
    if (!window.confirm(adminLabels.restoreJobStartConfirm)) return;
    setStarting(true);
    setStartError("");
    setStartMessage("");
    try {
      const startedJob = await startRestoreJob(liveJob.id);
      setLiveJob(startedJob);
      onJobUpdatedRef.current?.(startedJob);
      setStartMessage(adminLabels.restoreJobStartQueued);
      await refreshDetail();
    } catch (error) {
      setStartError(error instanceof Error ? error.message : adminLabels.restoreJobStartError);
    } finally {
      setStarting(false);
    }
  };
  const handleDelete = async () => {
    if (!canDelete) return;
    if (!window.confirm(adminLabels.restoreJobDeleteConfirm)) return;
    setDeleting(true);
    setDeleteError("");
    try {
      await deleteRestoreJob(liveJob.id);
      onDeleted?.();
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : adminLabels.restoreJobDeleteError);
    } finally {
      setDeleting(false);
    }
  };
  const uiStatus = mapRestoreJobUiStatus(liveJob.status);
  const showLogPlaceholder = !logLoading && !logExists;

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
      </dl>

      {uiStatus === "queued" && canStart && (
        <div className="backup-restore-manual-hint">
          <p className="text-muted">{adminLabels.restoreJobStartDescription}</p>
          <button type="button" className="btn danger" disabled={starting} onClick={() => void handleStart()}>
            {starting ? adminLabels.restoreJobStarting : adminLabels.restoreJobStart}
          </button>
        </div>
      )}
      {startError && <div className="restore-job-detail-error" role="alert">{startError}</div>}
      {startMessage && <p className="text-success">{startMessage}</p>}
      {deleteError && <div className="restore-job-detail-error" role="alert">{deleteError}</div>}
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
      {canDelete ? (
        <div className="form-actions">
          <button
            type="button"
            className="btn danger"
            disabled={deleting || uiStatus === "running"}
            title={uiStatus === "running" ? adminLabels.restoreJobDeleteRunningHint : undefined}
            onClick={() => void handleDelete()}
          >
            {deleting ? adminLabels.restoreJobDeleting : adminLabels.restoreJobDelete}
          </button>
        </div>
      ) : null}
    </Modal>
  );
}

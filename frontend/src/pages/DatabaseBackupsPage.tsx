import React from "react";
import {
  createSystemBackup,
  deleteSystemBackup,
  downloadSystemBackup,
  getSystemBackup,
  getRestoreJob,
  listSystemBackupsTable,
  listRestoreJobsTable,
  restoreSystemBackup,
  restoreSystemBackupFromUpload,
  ApiError,
} from "../api/systemAdmin";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { useRestoreJobPolling } from "../hooks/useRestoreJobPolling";
import { adminLabels } from "../labels/adminLabels";
import type { BackupFormat, SystemBackup, SystemBackupRestoreJobResponse } from "../types/systemBackup";
import type { BadgeVariant } from "../components/ui/Badge";
import { useModalFormCancel, useReportFormDirty } from "../hooks/useModalForm";
import {
  isTerminalRestoreJobStatus,
  mapRestoreJobUiStatus,
} from "../utils/restoreJobStatus";

function formatBytes(bytes: number | null): string {
  if (bytes == null || bytes <= 0) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return rest > 0 ? `${minutes}m ${rest}s` : `${minutes}m`;
}

function statusLabel(status: SystemBackup["status"]): string {
  if (status === "running") return adminLabels.statusRunning;
  if (status === "completed") return adminLabels.statusCompleted;
  return adminLabels.statusFailed;
}

function stageLabel(stage: SystemBackup["progress_stage"]): string {
  const map: Record<SystemBackup["progress_stage"], string> = {
    preparing: adminLabels.stagePreparing,
    dumping: adminLabels.stageDumping,
    compressing: adminLabels.stageCompressing,
    completed: adminLabels.stageCompleted,
    failed: adminLabels.stageFailed,
  };
  return map[stage] ?? stage;
}

function statusBadgeVariant(status: SystemBackup["status"]): BadgeVariant {
  if (status === "running") return "info";
  if (status === "completed") return "success";
  return "danger";
}

function restoreJobStatusLabel(status: SystemBackupRestoreJobResponse["status"]): string {
  const uiStatus = mapRestoreJobUiStatus(status);
  if (uiStatus === "queued") return adminLabels.restoreJobStatusQueued;
  if (uiStatus === "running") return adminLabels.restoreJobStatusRunning;
  if (uiStatus === "succeeded") return adminLabels.restoreJobStatusSucceeded;
  return adminLabels.restoreJobStatusFailed;
}

function restoreJobStatusBadgeVariant(status: SystemBackupRestoreJobResponse["status"]): BadgeVariant {
  const uiStatus = mapRestoreJobUiStatus(status);
  if (uiStatus === "queued") return "warning";
  if (uiStatus === "running") return "info";
  if (uiStatus === "succeeded") return "success";
  return "danger";
}

function restoreJobSourceLabel(sourceType: SystemBackupRestoreJobResponse["source_type"]): string {
  return sourceType === "existing_backup"
    ? adminLabels.restoreJobSourceExisting
    : adminLabels.restoreJobSourceUpload;
}

function restoreJobFileLabel(job: SystemBackupRestoreJobResponse): string {
  return job.backup_file_name ?? job.source_file_name;
}

function buildRestoreJobColumns(handlers: {
  onDetails: (job: SystemBackupRestoreJobResponse) => void;
}): UniversalDataTableColumn<SystemBackupRestoreJobResponse>[] {
  return [
    {
      key: "status",
      title: adminLabels.restoreJobColStatus,
      sortable: true,
      className: "col-status",
      render: (job) => (
        <Badge variant={restoreJobStatusBadgeVariant(job.status)}>{restoreJobStatusLabel(job.status)}</Badge>
      ),
    },
    {
      key: "source_type",
      title: adminLabels.restoreJobColSource,
      sortable: true,
      className: "col-format",
      render: (job) => restoreJobSourceLabel(job.source_type),
    },
    {
      key: "source_file_name",
      title: adminLabels.restoreJobColFile,
      sortable: true,
      className: "col-backup-name",
      render: (job) => (
        <span className="backup-file-name" title={restoreJobFileLabel(job)}>
          {restoreJobFileLabel(job)}
        </span>
      ),
    },
    {
      key: "requested_at",
      title: adminLabels.restoreJobColRequestedAt,
      sortable: true,
      className: "col-datetime",
      render: (job) => new Date(job.requested_at).toLocaleString("tr-TR"),
    },
    {
      key: "requested_by_email",
      title: adminLabels.restoreJobColRequestedBy,
      sortable: true,
      className: "col-created-by",
      render: (job) => job.requested_by_email ?? job.requested_by_user_id.slice(0, 8),
    },
    {
      key: "notes",
      title: adminLabels.restoreJobColNotes,
      sortable: true,
      className: "col-notes",
      render: (job) => job.notes ?? "—",
    },
    {
      key: "actions",
      title: adminLabels.colActions,
      sortable: false,
      className: "col-actions",
      render: (job) => (
        <div className="table-actions backups-table-actions">
          <button type="button" className="btn link" onClick={() => void handlers.onDetails(job)}>
            {adminLabels.actionDetails}
          </button>
        </div>
      ),
    },
  ];
}

function formatLabel(format: BackupFormat): string {
  if (format === "postgresql_dump") return adminLabels.formatPostgresqlDumpShort;
  if (format === "postgresql_sql") return adminLabels.formatPostgresqlSqlShort;
  return adminLabels.formatUniversalPackageShort;
}

function canRestoreBackup(backup: SystemBackup): boolean {
  return backup.status === "completed" && backup.backup_format === "postgresql_dump";
}

function restoreDisabledTitle(backup: SystemBackup): string | undefined {
  if (backup.status !== "completed") return adminLabels.restoreDisabledHint;
  if (backup.backup_format !== "postgresql_dump") return adminLabels.restoreNotDumpHint;
  return undefined;
}

const RESTORE_CONFIRM_TEXT = "RESTORE";
const DELETE_CONFIRM_TEXT = "DELETE";

function buildBackupColumns(handlers: {
  onDownload: (backup: SystemBackup) => void;
  onDetails: (backup: SystemBackup) => void;
  downloadingId: string | null;
}): UniversalDataTableColumn<SystemBackup>[] {
  return [
    {
      key: "file_name",
      title: adminLabels.colName,
      sortable: true,
      className: "col-backup-name",
      render: (backup) => (
        <span className="backup-file-name" title={backup.file_name}>
          {backup.file_name}
        </span>
      ),
    },
    {
      key: "backup_format",
      title: adminLabels.colFormat,
      sortable: true,
      className: "col-format",
      render: (backup) => formatLabel(backup.backup_format),
    },
    {
      key: "started_at",
      title: adminLabels.colCreatedAt,
      sortable: true,
      className: "col-datetime",
      render: (backup) => new Date(backup.started_at).toLocaleString("tr-TR"),
    },
    {
      key: "created_by_email",
      title: adminLabels.colCreatedBy,
      sortable: true,
      className: "col-created-by",
      render: (backup) => {
        const label = backup.created_by_email ?? backup.created_by.slice(0, 8);
        return (
          <span className="backup-created-by" title={backup.created_by_email ?? backup.created_by}>
            {label}
          </span>
        );
      },
    },
    {
      key: "file_size",
      title: adminLabels.colSize,
      sortable: true,
      className: "col-size",
      render: (backup) => formatBytes(backup.file_size),
    },
    {
      key: "duration_seconds",
      title: adminLabels.colDuration,
      sortable: true,
      className: "col-duration",
      render: (backup) => formatDuration(backup.duration_seconds),
    },
    {
      key: "status",
      title: adminLabels.colStatus,
      sortable: true,
      className: "col-status",
      render: (backup) => (
        <div className="backup-status-cell">
          <Badge variant={statusBadgeVariant(backup.status)}>{statusLabel(backup.status)}</Badge>
          {backup.status === "running" && (
            <div className="backup-progress-hint">{stageLabel(backup.progress_stage)}</div>
          )}
        </div>
      ),
    },
    {
      key: "actions",
      title: adminLabels.colActions,
      sortable: false,
      className: "col-actions",
      render: (backup) => (
        <div className="table-actions backups-table-actions">
          <button
            type="button"
            className="btn link"
            disabled={backup.status !== "completed" || handlers.downloadingId === backup.id}
            onClick={() => void handlers.onDownload(backup)}
          >
            {adminLabels.actionDownload}
          </button>
          <button type="button" className="btn link" onClick={() => void handlers.onDetails(backup)}>
            {adminLabels.actionDetails}
          </button>
        </div>
      ),
    },
  ];
}

interface CreateBackupModalContentProps {
  notes: string;
  onNotesChange: (value: string) => void;
  backupFormat: BackupFormat;
  onBackupFormatChange: (value: BackupFormat) => void;
  createError: string | null;
  creating: boolean;
  onCancel: () => void;
  onSubmit: () => void;
}

function CreateBackupModalContent({
  notes,
  onNotesChange,
  backupFormat,
  onBackupFormatChange,
  createError,
  creating,
  onCancel,
  onSubmit,
}: CreateBackupModalContentProps) {
  const baseline = React.useMemo(
    () => ({ notes: "", backupFormat: "postgresql_dump" as BackupFormat }),
    [],
  );
  useReportFormDirty({ notes, backupFormat }, baseline);
  const handleCancel = useModalFormCancel(onCancel);

  return (
    <>
      <fieldset className="backup-format-options">
        <legend>{adminLabels.formatLabel}</legend>
        <label className="backup-format-option">
          <input
            type="radio"
            name="backup_format"
            value="postgresql_dump"
            checked={backupFormat === "postgresql_dump"}
            onChange={() => onBackupFormatChange("postgresql_dump")}
          />
          <span>
            <strong>{adminLabels.formatPostgresqlDump}</strong>
            <span className="text-muted">{adminLabels.formatPostgresqlDumpDesc}</span>
          </span>
        </label>
        <label className="backup-format-option">
          <input
            type="radio"
            name="backup_format"
            value="postgresql_sql"
            checked={backupFormat === "postgresql_sql"}
            onChange={() => onBackupFormatChange("postgresql_sql")}
          />
          <span>
            <strong>{adminLabels.formatPostgresqlSql}</strong>
            <span className="text-muted">{adminLabels.formatPostgresqlSqlDesc}</span>
          </span>
        </label>
        <label className="backup-format-option">
          <input
            type="radio"
            name="backup_format"
            value="universal_data_package"
            checked={backupFormat === "universal_data_package"}
            onChange={() => onBackupFormatChange("universal_data_package")}
          />
          <span>
            <strong>{adminLabels.formatUniversalPackage}</strong>
            <span className="text-muted">{adminLabels.formatUniversalPackageDesc}</span>
          </span>
        </label>
      </fieldset>
      <label className="form-field">
        <span>{adminLabels.notesLabel}</span>
        <textarea
          rows={4}
          value={notes}
          onChange={(e) => onNotesChange(e.target.value)}
          placeholder={adminLabels.notesPlaceholder}
          maxLength={2000}
        />
      </label>
      <p className="text-muted">{adminLabels.notesHint}</p>
      {createError && <p className="form-error">{createError}</p>}
      <div className="modal-actions">
        <button type="button" className="btn secondary" onClick={handleCancel}>
          {adminLabels.cancel}
        </button>
        <button type="button" className="btn primary" disabled={creating} onClick={onSubmit}>
          {creating ? "…" : adminLabels.startBackup}
        </button>
      </div>
    </>
  );
}

interface RestoreBackupConfirmModalProps {
  backup: SystemBackup;
  restoring: boolean;
  error: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

function RestoreBackupConfirmModal({
  backup,
  restoring,
  error,
  onCancel,
  onConfirm,
}: RestoreBackupConfirmModalProps) {
  const [confirmText, setConfirmText] = React.useState("");
  const canConfirm = confirmText === RESTORE_CONFIRM_TEXT;

  return (
    <Modal title={adminLabels.restoreDatabaseTitle} onClose={onCancel}>
      <div className="backup-restore-confirm">
        <p className="text-danger">{adminLabels.restoreWarning}</p>
        <dl className="detail-list backup-restore-summary">
          <dt>{adminLabels.colName}</dt>
          <dd>{backup.file_name}</dd>
          <dt>{adminLabels.colCreatedAt}</dt>
          <dd>{new Date(backup.started_at).toLocaleString("tr-TR")}</dd>
          <dt>{adminLabels.colSize}</dt>
          <dd>{formatBytes(backup.file_size)}</dd>
          <dt>{adminLabels.detailChecksum}</dt>
          <dd className="mono">{backup.checksum ?? "—"}</dd>
          <dt>{adminLabels.detailFormat}</dt>
          <dd>{formatLabel(backup.backup_format)}</dd>
        </dl>
        <p className="text-muted backup-restore-manual-hint">{adminLabels.restoreJobManualHint}</p>
        <label className="form-field">
          <span>{adminLabels.restoreConfirmLabel}</span>
          <input
            type="text"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder={adminLabels.restoreConfirmPlaceholder}
            autoComplete="off"
            spellCheck={false}
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="btn secondary" onClick={onCancel} disabled={restoring}>
            {adminLabels.cancel}
          </button>
          <button
            type="button"
            className="btn danger"
            disabled={restoring || !canConfirm}
            onClick={onConfirm}
          >
            {restoring ? "…" : adminLabels.restoreDatabaseButton}
          </button>
        </div>
      </div>
    </Modal>
  );
}

interface DeleteBackupConfirmModalProps {
  backup: SystemBackup;
  deleting: boolean;
  error: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

function DeleteBackupConfirmModal({
  backup,
  deleting,
  error,
  onCancel,
  onConfirm,
}: DeleteBackupConfirmModalProps) {
  const [confirmText, setConfirmText] = React.useState("");
  const canConfirm = confirmText === DELETE_CONFIRM_TEXT;

  return (
    <Modal title={adminLabels.deleteBackupTitle} onClose={onCancel}>
      <div className="backup-delete-confirm">
        <p className="text-danger">{adminLabels.deleteBackupWarning}</p>
        <p>
          <strong>{adminLabels.colName}:</strong> {backup.file_name}
        </p>
        <label className="form-field">
          <span>{adminLabels.deleteConfirmLabel}</span>
          <input
            type="text"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder={adminLabels.deleteConfirmPlaceholder}
            autoComplete="off"
            spellCheck={false}
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="btn secondary" onClick={onCancel} disabled={deleting}>
            {adminLabels.cancel}
          </button>
          <button
            type="button"
            className="btn danger"
            disabled={deleting || !canConfirm}
            onClick={onConfirm}
          >
            {deleting ? "…" : adminLabels.actionDelete}
          </button>
        </div>
      </div>
    </Modal>
  );
}

interface RestoreFromFileModalProps {
  notes: string;
  selectedFile: File | null;
  acknowledge: boolean;
  confirmText: string;
  restoring: boolean;
  error: string | null;
  onNotesChange: (value: string) => void;
  onFileChange: (file: File | null) => void;
  onAcknowledgeChange: (value: boolean) => void;
  onConfirmTextChange: (value: string) => void;
  onCancel: () => void;
  onSubmit: () => void;
}

function RestoreFromFileModal({
  notes,
  selectedFile,
  acknowledge,
  confirmText,
  restoring,
  error,
  onNotesChange,
  onFileChange,
  onAcknowledgeChange,
  onConfirmTextChange,
  onCancel,
  onSubmit,
}: RestoreFromFileModalProps) {
  const canSubmit =
    selectedFile != null &&
    selectedFile.size > 0 &&
    selectedFile.name.toLowerCase().endsWith(".dump") &&
    acknowledge &&
    confirmText === RESTORE_CONFIRM_TEXT;

  return (
    <Modal title={adminLabels.restoreFromFileTitle} onClose={onCancel}>
      <div className="backup-restore-upload">
        <p className="text-danger">{adminLabels.restoreWarning}</p>
        <label className="form-field">
          <span>{adminLabels.restoreUploadLabel}</span>
          <input
            type="file"
            accept=".dump"
            onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
          />
        </label>
        <p className="text-muted">{adminLabels.restoreUploadHint}</p>
        {selectedFile && (
          <p>
            <strong>{adminLabels.restoreFileSizeLabel}:</strong> {formatBytes(selectedFile.size)}
          </p>
        )}
        <label className="form-field">
          <span>{adminLabels.notesLabel}</span>
          <textarea
            rows={3}
            value={notes}
            onChange={(e) => onNotesChange(e.target.value)}
            placeholder={adminLabels.notesPlaceholder}
            maxLength={2000}
          />
        </label>
        <label className="backup-restore-acknowledge">
          <input
            type="checkbox"
            checked={acknowledge}
            onChange={(e) => onAcknowledgeChange(e.target.checked)}
          />
          <span>{adminLabels.restoreAcknowledge}</span>
        </label>
        <label className="form-field">
          <span>{adminLabels.restoreConfirmLabel}</span>
          <input
            type="text"
            value={confirmText}
            onChange={(e) => onConfirmTextChange(e.target.value)}
            placeholder={adminLabels.restoreConfirmPlaceholder}
            autoComplete="off"
            spellCheck={false}
          />
        </label>
        <p className="text-muted backup-restore-manual-hint">{adminLabels.restoreJobManualHint}</p>
        {error && <p className="form-error">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="btn secondary" onClick={onCancel} disabled={restoring}>
            {adminLabels.cancel}
          </button>
          <button type="button" className="btn danger" disabled={restoring || !canSubmit} onClick={onSubmit}>
            {restoring ? "…" : adminLabels.restoreFromFileButton}
          </button>
        </div>
      </div>
    </Modal>
  );
}

export function DatabaseBackupsPage() {
  const table = useServerDataTable<SystemBackup>({
    fetchFn: listSystemBackupsTable,
    defaultSort: { field: "started_at", direction: "desc" },
    pageSize: 50,
    urlSync: true,
    urlPath: "/admin/system/backups",
  });

  const restoreJobsTable = useServerDataTable<SystemBackupRestoreJobResponse>({
    fetchFn: listRestoreJobsTable,
    defaultSort: { field: "requested_at", direction: "desc" },
    pageSize: 20,
    urlSync: false,
  });

  const handleRestoreJobTerminal = React.useCallback(
    (job: SystemBackupRestoreJobResponse) => {
      void restoreJobsTable.refresh();
      if (job.status === "completed") {
        setNotice(adminLabels.restoreJobPollSuccess);
        setRestorePollError(null);
      } else if (job.status === "failed") {
        setNotice(null);
        setRestorePollError(job.error_message ?? adminLabels.restoreJobPollFailed);
      }
    },
    [restoreJobsTable.refresh],
  );

  const { trackedJobs, trackRestoreJob, syncRestoreJobsFromList } = useRestoreJobPolling({
    onTerminal: handleRestoreJobTerminal,
  });

  const [notice, setNotice] = React.useState<string | null>(null);
  const [restorePollError, setRestorePollError] = React.useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = React.useState(false);
  const [notes, setNotes] = React.useState("");
  const [backupFormat, setBackupFormat] = React.useState<BackupFormat>("postgresql_dump");
  const [creating, setCreating] = React.useState(false);
  const [createError, setCreateError] = React.useState<string | null>(null);
  const [detailBackup, setDetailBackup] = React.useState<SystemBackup | null>(null);
  const [restoreTarget, setRestoreTarget] = React.useState<SystemBackup | null>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<SystemBackup | null>(null);
  const [showRestoreUploadModal, setShowRestoreUploadModal] = React.useState(false);
  const [restoreUploadNotes, setRestoreUploadNotes] = React.useState("");
  const [restoreUploadFile, setRestoreUploadFile] = React.useState<File | null>(null);
  const [restoreUploadAcknowledge, setRestoreUploadAcknowledge] = React.useState(false);
  const [restoreUploadConfirmText, setRestoreUploadConfirmText] = React.useState("");
  const [restoring, setRestoring] = React.useState(false);
  const [restoreError, setRestoreError] = React.useState<string | null>(null);
  const [deleting, setDeleting] = React.useState(false);
  const [deleteError, setDeleteError] = React.useState<string | null>(null);
  const [pollingIds, setPollingIds] = React.useState<Set<string>>(new Set());
  const [detailRestoreJob, setDetailRestoreJob] = React.useState<SystemBackupRestoreJobResponse | null>(null);
  const [downloadingId, setDownloadingId] = React.useState<string | null>(null);

  const activeTrackedJobs = React.useMemo(
    () => [...trackedJobs.values()].filter((job) => !isTerminalRestoreJobStatus(job.status)),
    [trackedJobs],
  );

  const visibleDetailRestoreJob = React.useMemo(() => {
    if (!detailRestoreJob) return null;
    return trackedJobs.get(detailRestoreJob.id) ?? detailRestoreJob;
  }, [detailRestoreJob, trackedJobs]);

  React.useEffect(() => {
    syncRestoreJobsFromList(restoreJobsTable.items);
  }, [restoreJobsTable.items, syncRestoreJobsFromList]);

  React.useEffect(() => {
    const running = new Set(table.items.filter((item) => item.status === "running").map((item) => item.id));
    setPollingIds((prev) => {
      const next = new Set(prev);
      for (const id of running) next.add(id);
      return next;
    });
  }, [table.items]);

  React.useEffect(() => {
    if (pollingIds.size === 0) return;
    const timer = window.setInterval(() => {
      void (async () => {
        let shouldRefresh = false;
        for (const id of pollingIds) {
          try {
            const backup = await getSystemBackup(id);
            if (backup.status !== "running") {
              shouldRefresh = true;
              setPollingIds((prev) => {
                const next = new Set(prev);
                next.delete(id);
                return next;
              });
            }
          } catch {
            /* polling */
          }
        }
        if (shouldRefresh) await table.refresh();
      })();
    }, 1500);
    return () => window.clearInterval(timer);
  }, [pollingIds, table.refresh]);

  const closeCreateModal = React.useCallback(() => {
    setShowCreateModal(false);
    setBackupFormat("postgresql_dump");
    setNotes("");
    setCreateError(null);
  }, []);

  const closeDetailModal = React.useCallback(() => setDetailBackup(null), []);
  const closeRestoreJobDetailModal = React.useCallback(() => setDetailRestoreJob(null), []);

  const closeRestoreConfirm = React.useCallback(() => {
    setRestoreTarget(null);
    setRestoreError(null);
  }, []);

  const closeDeleteConfirm = React.useCallback(() => {
    setDeleteTarget(null);
    setDeleteError(null);
  }, []);

  const closeRestoreUploadModal = React.useCallback(() => {
    setShowRestoreUploadModal(false);
    setRestoreUploadNotes("");
    setRestoreUploadFile(null);
    setRestoreUploadAcknowledge(false);
    setRestoreUploadConfirmText("");
    setRestoreError(null);
  }, []);

  const handleRestoreBackup = async () => {
    if (!restoreTarget) return;
    setRestoring(true);
    setRestoreError(null);
    setRestorePollError(null);
    try {
      const job = await restoreSystemBackup(restoreTarget.id);
      trackRestoreJob(job);
      setRestoreTarget(null);
      setDetailBackup(null);
      setNotice(adminLabels.restoreSuccess);
      await restoreJobsTable.refresh();
    } catch (err) {
      setRestoreError(err instanceof ApiError ? err.message : adminLabels.restoreError);
    } finally {
      setRestoring(false);
    }
  };

  const handleRestoreFromUpload = async () => {
    if (!restoreUploadFile) return;
    setRestoring(true);
    setRestoreError(null);
    setRestorePollError(null);
    try {
      const job = await restoreSystemBackupFromUpload(restoreUploadFile, restoreUploadNotes.trim() || null);
      trackRestoreJob(job);
      closeRestoreUploadModal();
      setNotice(adminLabels.restoreSuccess);
      await restoreJobsTable.refresh();
    } catch (err) {
      setRestoreError(err instanceof ApiError ? err.message : adminLabels.restoreError);
    } finally {
      setRestoring(false);
    }
  };

  const handleDeleteBackup = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteSystemBackup(deleteTarget.id);
      setDeleteTarget(null);
      setDetailBackup(null);
      setNotice(adminLabels.deleteSuccess);
      await table.refresh();
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : adminLabels.deleteError);
    } finally {
      setDeleting(false);
    }
  };

  const handleCreateBackup = async () => {
    setCreating(true);
    setNotice(null);
    setCreateError(null);
    try {
      const created = await createSystemBackup(notes.trim() || null, backupFormat);
      setShowCreateModal(false);
      setNotes("");
      setNotice(adminLabels.backupStarting);
      setPollingIds((prev) => new Set(prev).add(created.id));
      await table.refresh();
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.message : adminLabels.createError);
    } finally {
      setCreating(false);
    }
  };

  const handleDownload = async (backup: SystemBackup) => {
    setDownloadingId(backup.id);
    try {
      await downloadSystemBackup(backup.id, backup.file_name);
      await table.refresh();
    } catch (err) {
      void err;
    } finally {
      setDownloadingId(null);
    }
  };

  const openDetails = async (backup: SystemBackup) => {
    try {
      setDetailBackup(await getSystemBackup(backup.id));
    } catch (err) {
      void err;
    }
  };

  const openRestoreJobDetails = async (job: SystemBackupRestoreJobResponse) => {
    try {
      const fresh = await getRestoreJob(job.id);
      setDetailRestoreJob(fresh);
      if (!isTerminalRestoreJobStatus(fresh.status)) {
        trackRestoreJob(fresh);
      }
    } catch {
      /* ignore */
    }
  };

  const columns = React.useMemo(
    () =>
      buildBackupColumns({
        onDownload: handleDownload,
        onDetails: openDetails,
        downloadingId,
      }),
    [downloadingId],
  );

  const restoreJobColumns = React.useMemo(
    () => buildRestoreJobColumns({ onDetails: openRestoreJobDetails }),
    [],
  );

  return (
    <div>
      <PageHeader
        title={adminLabels.backupsTitle}
        subtitle={adminLabels.backupsSubtitle}
        actions={[
          {
            id: "new-backup",
            label: adminLabels.newBackup,
            onClick: () => setShowCreateModal(true),
            variant: "primary",
          },
          {
            id: "restore-from-file",
            label: adminLabels.restoreFromFile,
            onClick: () => setShowRestoreUploadModal(true),
            variant: "secondary",
          },
        ]}
      />

      {notice && <p className="text-muted">{notice}</p>}
      {restorePollError && <p className="form-error">{restorePollError}</p>}

      {activeTrackedJobs.length > 0 && (
        <div className="restore-job-polling-banner" aria-live="polite">
          <p className="text-muted">{adminLabels.restoreJobTracking}</p>
          <ul className="restore-job-polling-list">
            {activeTrackedJobs.map((job) => (
              <li key={job.id}>
                <Badge variant={restoreJobStatusBadgeVariant(job.status)}>
                  {restoreJobStatusLabel(job.status)}
                </Badge>
                <span className="backup-file-name">{restoreJobFileLabel(job)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <UniversalDataTable
        table={table}
        columns={columns}
        rowKey={(backup) => backup.id}
        skeletonCols={8}
        className="backups-table"
        emptyState={
          <EmptyState title={adminLabels.backupsEmpty} description={adminLabels.backupsEmptyDescription} />
        }
      />

      <section className="restore-jobs-section">
        <h2>{adminLabels.restoreJobsTitle}</h2>
        <p className="text-muted">{adminLabels.restoreJobsSubtitle}</p>
        <UniversalDataTable
          table={restoreJobsTable}
          columns={restoreJobColumns}
          rowKey={(job) => job.id}
          skeletonCols={7}
          className="restore-jobs-table"
          emptyState={
            <EmptyState
              title={adminLabels.restoreJobEmpty}
              description={adminLabels.restoreJobEmptyDescription}
            />
          }
        />
      </section>

      {showCreateModal && (
        <Modal title={adminLabels.newBackupTitle} onClose={closeCreateModal}>
          <CreateBackupModalContent
            notes={notes}
            onNotesChange={setNotes}
            backupFormat={backupFormat}
            onBackupFormatChange={setBackupFormat}
            createError={createError}
            creating={creating}
            onCancel={closeCreateModal}
            onSubmit={() => void handleCreateBackup()}
          />
        </Modal>
      )}

      {detailBackup && (
        <Modal title={adminLabels.detailsTitle} onClose={closeDetailModal}>
          <dl className="detail-list">
            <dt>{adminLabels.colName}</dt>
            <dd>{detailBackup.file_name}</dd>
            <dt>{adminLabels.detailFormat}</dt>
            <dd>{formatLabel(detailBackup.backup_format)}</dd>
            <dt>{adminLabels.colStatus}</dt>
            <dd>
              {statusLabel(detailBackup.status)}
              {detailBackup.status === "running" && ` — ${stageLabel(detailBackup.progress_stage)}`}
            </dd>
            <dt>{adminLabels.colCreatedAt}</dt>
            <dd>{new Date(detailBackup.started_at).toLocaleString("tr-TR")}</dd>
            <dt>{adminLabels.colCreatedBy}</dt>
            <dd>{detailBackup.created_by_email ?? detailBackup.created_by}</dd>
            <dt>{adminLabels.colSize}</dt>
            <dd>{formatBytes(detailBackup.file_size)}</dd>
            <dt>{adminLabels.colDuration}</dt>
            <dd>{formatDuration(detailBackup.duration_seconds)}</dd>
            <dt>{adminLabels.colNotes}</dt>
            <dd>{detailBackup.notes ?? "—"}</dd>
            <dt>{adminLabels.detailChecksum}</dt>
            <dd className="mono">{detailBackup.checksum ?? "—"}</dd>
            {detailBackup.manifest_json && (
              <>
                <dt>{adminLabels.detailManifest}</dt>
                <dd className="mono backup-manifest-preview">
                  {JSON.stringify(detailBackup.manifest_json, null, 2)}
                </dd>
              </>
            )}
            <dt>{adminLabels.detailDownloadCount}</dt>
            <dd>{detailBackup.download_count}</dd>
            {detailBackup.error_message && (
              <>
                <dt>{adminLabels.detailError}</dt>
                <dd className="form-error">{detailBackup.error_message}</dd>
              </>
            )}
          </dl>
          <div className="backup-detail-actions">
            <button
              type="button"
              className={`btn link${canRestoreBackup(detailBackup) ? "" : " disabled-action"}`}
              disabled={!canRestoreBackup(detailBackup)}
              title={restoreDisabledTitle(detailBackup)}
              onClick={() => setRestoreTarget(detailBackup)}
            >
              {adminLabels.actionRestore}
            </button>
            <button
              type="button"
              className="btn link"
              onClick={() => setDeleteTarget(detailBackup)}
            >
              {adminLabels.actionDelete}
            </button>
          </div>
        </Modal>
      )}

      {restoreTarget && (
        <RestoreBackupConfirmModal
          backup={restoreTarget}
          restoring={restoring}
          error={restoreError}
          onCancel={closeRestoreConfirm}
          onConfirm={() => void handleRestoreBackup()}
        />
      )}

      {deleteTarget && (
        <DeleteBackupConfirmModal
          backup={deleteTarget}
          deleting={deleting}
          error={deleteError}
          onCancel={closeDeleteConfirm}
          onConfirm={() => void handleDeleteBackup()}
        />
      )}

      {visibleDetailRestoreJob && (
        <Modal title={adminLabels.restoreJobDetailsTitle} onClose={closeRestoreJobDetailModal}>
          <dl className="detail-list">
            <dt>{adminLabels.restoreJobColStatus}</dt>
            <dd>
              <Badge variant={restoreJobStatusBadgeVariant(visibleDetailRestoreJob.status)}>
                {restoreJobStatusLabel(visibleDetailRestoreJob.status)}
              </Badge>
            </dd>
            <dt>{adminLabels.restoreJobColSource}</dt>
            <dd>{restoreJobSourceLabel(visibleDetailRestoreJob.source_type)}</dd>
            <dt>{adminLabels.restoreJobColFile}</dt>
            <dd>{restoreJobFileLabel(visibleDetailRestoreJob)}</dd>
            <dt>{adminLabels.restoreJobColRequestedAt}</dt>
            <dd>{new Date(visibleDetailRestoreJob.requested_at).toLocaleString("tr-TR")}</dd>
            <dt>{adminLabels.restoreJobColRequestedBy}</dt>
            <dd>{visibleDetailRestoreJob.requested_by_email ?? visibleDetailRestoreJob.requested_by_user_id}</dd>
            <dt>{adminLabels.restoreJobColNotes}</dt>
            <dd className="restore-job-notes-preview">
              {visibleDetailRestoreJob.notes?.trim() ? visibleDetailRestoreJob.notes : "—"}
            </dd>
            <dt>{adminLabels.detailChecksum}</dt>
            <dd className="mono">{visibleDetailRestoreJob.checksum_sha256 ?? "—"}</dd>
            {visibleDetailRestoreJob.backup_file_name && (
              <>
                <dt>{adminLabels.restoreJobDetailBackupSummary}</dt>
                <dd>
                  {visibleDetailRestoreJob.backup_file_name}
                  {visibleDetailRestoreJob.backup_format ? ` (${visibleDetailRestoreJob.backup_format})` : ""}
                </dd>
              </>
            )}
            <dt>{adminLabels.restoreJobDetailLogPath}</dt>
            <dd className="mono">{visibleDetailRestoreJob.restore_log_path ?? "—"}</dd>
            {visibleDetailRestoreJob.error_message && (
              <>
                <dt>{adminLabels.restoreJobDetailError}</dt>
                <dd className="form-error">{visibleDetailRestoreJob.error_message}</dd>
              </>
            )}
          </dl>
          {mapRestoreJobUiStatus(visibleDetailRestoreJob.status) === "queued" && (
            <p className="text-muted backup-restore-manual-hint">{adminLabels.restoreJobManualHint}</p>
          )}
        </Modal>
      )}

      {showRestoreUploadModal && (
        <RestoreFromFileModal
          notes={restoreUploadNotes}
          selectedFile={restoreUploadFile}
          acknowledge={restoreUploadAcknowledge}
          confirmText={restoreUploadConfirmText}
          restoring={restoring}
          error={restoreError}
          onNotesChange={setRestoreUploadNotes}
          onFileChange={setRestoreUploadFile}
          onAcknowledgeChange={setRestoreUploadAcknowledge}
          onConfirmTextChange={setRestoreUploadConfirmText}
          onCancel={closeRestoreUploadModal}
          onSubmit={() => void handleRestoreFromUpload()}
        />
      )}
    </div>
  );
}

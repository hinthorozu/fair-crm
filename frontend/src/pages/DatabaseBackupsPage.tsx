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
import { Banner } from "../components/ui/Banner";
import { EmptyState } from "../components/ui/EmptyState";
import { RestoreJobDetailModal } from "../components/admin/RestoreJobDetailModal";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import {
  CheckboxField,
  FieldError,
  RadioField,
  TextInput,
  TextareaInput,
} from "../components/ui/form";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { TableRowActions } from "../components/ui/TableRowActions";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { useRestoreJobPolling } from "../hooks/useRestoreJobPolling";
import { adminLabels } from "../labels/adminLabels";
import type { BackupFormat, DatabaseKey, SystemBackup, SystemBackupRestoreJobResponse } from "../types/systemBackup";
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

function databaseKeyLabel(key: DatabaseKey): string {
  if (key === "kyrox_core") return adminLabels.databaseKeyKyroxCore;
  return adminLabels.databaseKeyFairCrm;
}

function restoreWarningForDatabase(key: DatabaseKey): string {
  if (key === "kyrox_core") return adminLabels.restoreWarningKyroxCore;
  return adminLabels.restoreWarningFairCrm;
}

function restoreUploadWarningForDatabase(key: DatabaseKey): string {
  if (key === "kyrox_core") return adminLabels.restoreUploadWarningKyroxCore;
  return adminLabels.restoreUploadWarningFairCrm;
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
      key: "source_database_key",
      title: adminLabels.restoreJobColSourceDatabase,
      sortable: true,
      className: "col-format",
      render: (job) => databaseKeyLabel(job.source_database_key),
    },
    {
      key: "target_database_key",
      title: adminLabels.restoreJobColTargetDatabase,
      sortable: true,
      className: "col-format",
      render: (job) => databaseKeyLabel(job.target_database_key),
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
        <TableRowActions className="backups-table-actions">
          <button type="button" className="btn link" onClick={() => void handlers.onDetails(job)}>
            {adminLabels.actionDetails}
          </button>
        </TableRowActions>
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

function inferDatabaseKeyFromFileName(fileName: string): DatabaseKey | null {
  const name = fileName.toLowerCase();
  if (name.startsWith("kyrox_core_backup_")) return "kyrox_core";
  if (name.startsWith("fair_crm_backup_") || name.startsWith("fair_crm_data_package_")) return "fair_crm";
  if (name.startsWith("faircrm_backup_") || name.startsWith("faircrm_data_package_")) return "fair_crm";
  return null;
}

function renderBackupDatabaseCell(backup: SystemBackup): React.ReactNode {
  return (
    <div className="backup-database-cell">
      <span className="backup-database-label">
        {backup.database_label ?? databaseKeyLabel(backup.database_key)}
      </span>
      <span className="backup-database-key">{backup.database_key}</span>
    </div>
  );
}

function buildBackupColumns(handlers: {
  onDownload: (backup: SystemBackup) => void;
  onDetails: (backup: SystemBackup) => void;
  downloadingId: string | null;
}): UniversalDataTableColumn<SystemBackup>[] {
  return [
    {
      key: "database_key",
      title: adminLabels.colDatabase,
      sortable: true,
      sortField: "database_key",
      className: "col-database",
      render: (backup) => renderBackupDatabaseCell(backup),
    },
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
      key: "status",
      title: adminLabels.colStatus,
      sortable: true,
      className: "col-status",
      render: (backup) => (
        <div className="backup-status-cell">
          <Badge variant={statusBadgeVariant(backup.status)}>{statusLabel(backup.status)}</Badge>
          {backup.status === "running" && (
            <span className="backup-progress-hint">{stageLabel(backup.progress_stage)}</span>
          )}
        </div>
      ),
    },
    {
      key: "file_size",
      title: adminLabels.colSize,
      sortable: true,
      className: "col-size",
      render: (backup) => formatBytes(backup.file_size),
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
      key: "actions",
      title: adminLabels.colActions,
      sortable: false,
      className: "col-actions",
      render: (backup) => (
        <TableRowActions className="backups-table-actions">
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
        </TableRowActions>
      ),
    },
  ];
}

const DATABASE_KEY_OPTIONS: Array<{
  value: DatabaseKey;
  title: string;
  description: string;
}> = [
  {
    value: "kyrox_core",
    title: adminLabels.databaseKeyKyroxCore,
    description: adminLabels.databaseKeyKyroxCoreDesc,
  },
  {
    value: "fair_crm",
    title: adminLabels.databaseKeyFairCrm,
    description: adminLabels.databaseKeyFairCrmDesc,
  },
];

const BACKUP_FORMAT_OPTIONS: Array<{
  value: BackupFormat;
  title: string;
  description: string;
}> = [
  {
    value: "postgresql_dump",
    title: adminLabels.formatPostgresqlDump,
    description: adminLabels.formatPostgresqlDumpDesc,
  },
  {
    value: "postgresql_sql",
    title: adminLabels.formatPostgresqlSql,
    description: adminLabels.formatPostgresqlSqlDesc,
  },
  {
    value: "universal_data_package",
    title: adminLabels.formatUniversalPackage,
    description: adminLabels.formatUniversalPackageDesc,
  },
];

interface CreateBackupModalContentProps {
  notes: string;
  onNotesChange: (value: string) => void;
  backupFormat: BackupFormat;
  onBackupFormatChange: (value: BackupFormat) => void;
  selectedDatabaseKeys: DatabaseKey[];
  onDatabaseKeysChange: (value: DatabaseKey[]) => void;
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
  selectedDatabaseKeys,
  onDatabaseKeysChange,
  createError,
  creating,
  onCancel,
  onSubmit,
}: CreateBackupModalContentProps) {
  const baseline = React.useMemo(
    () => ({
      notes: "",
      backupFormat: "postgresql_dump" as BackupFormat,
      selectedDatabaseKeys: ["fair_crm"] as DatabaseKey[],
    }),
    [],
  );
  useReportFormDirty({ notes, backupFormat, selectedDatabaseKeys }, baseline);

  const toggleDatabaseKey = (key: DatabaseKey) => {
    onDatabaseKeysChange(
      selectedDatabaseKeys.includes(key)
        ? selectedDatabaseKeys.filter((item) => item !== key)
        : [...selectedDatabaseKeys, key],
    );
  };

  const includesKyroxCore = selectedDatabaseKeys.includes("kyrox_core");
  const visibleFormatOptions = BACKUP_FORMAT_OPTIONS.filter(
    (option) => !(includesKyroxCore && option.value === "universal_data_package"),
  );

  React.useEffect(() => {
    if (includesKyroxCore && backupFormat === "universal_data_package") {
      onBackupFormatChange("postgresql_dump");
    }
  }, [includesKyroxCore, backupFormat, onBackupFormatChange]);

  return (
    <div className="backup-create-modal">
      <section className="backup-create-modal-section">
        <p className="form-section-title">{adminLabels.databaseKeysLabel}</p>
        <div className="backup-database-options" role="group" aria-label={adminLabels.databaseKeysLabel}>
          {DATABASE_KEY_OPTIONS.map((option) => {
            const selected = selectedDatabaseKeys.includes(option.value);
            const inputId = `backup-create-db-${option.value}`;
            return (
              <div
                key={option.value}
                className={`backup-database-option${selected ? " is-selected" : ""}`}
              >
                <CheckboxField
                  id={inputId}
                  label={option.title}
                  checked={selected}
                  onChange={() => toggleDatabaseKey(option.value)}
                  hideLabel
                  className="backup-database-option-control"
                />
                <label htmlFor={inputId} className="backup-database-option-title">
                  {option.title}
                </label>
                <span className="backup-database-option-desc field-hint">{option.description}</span>
              </div>
            );
          })}
        </div>
        {!canSubmit && <FieldError>{adminLabels.databaseKeysRequired}</FieldError>}
      </section>

      <section className="backup-create-modal-section">
        <p className="form-section-title">{adminLabels.formatLabel}</p>
        <div className="backup-format-cards" role="radiogroup" aria-label={adminLabels.formatLabel}>
          {visibleFormatOptions.map((option) => {
            const selected = backupFormat === option.value;
            const inputId = `backup-format-${option.value}`;
            return (
              <div
                key={option.value}
                className={`backup-format-card${selected ? " is-selected" : ""}`}
              >
                <RadioField
                  id={inputId}
                  name="backup_format"
                  label={option.title}
                  value={option.value}
                  checked={selected}
                  onChange={(value) => onBackupFormatChange(value as BackupFormat)}
                  hideLabel
                  className="backup-format-card-radio"
                  inputClassName="backup-format-card-radio"
                />
                <label htmlFor={inputId} className="backup-format-card-title">
                  {option.title}
                </label>
                <span className="backup-format-card-desc field-hint">{option.description}</span>
              </div>
            );
          })}
        </div>
      </section>

      <label className="field backup-create-modal-notes">
        <span className="field-label">{adminLabels.notesLabel}</span>
        <TextareaInput
          id="backup-create-notes"
          rows={3}
          value={notes}
          onChange={(e) => onNotesChange(e.target.value)}
          placeholder={adminLabels.notesPlaceholder}
          maxLength={2000}
        />
        <span className="field-hint">{adminLabels.notesHint}</span>
      </label>

      {createError ? <FieldError>{createError}</FieldError> : null}
    </div>
  );
}

/** Stable footer actions for create-backup Modal (ADR-032 sticky footer). */
function CreateBackupModalFooter({
  creating,
  canSubmit,
  onCancel,
  onSubmit,
}: {
  creating: boolean;
  canSubmit: boolean;
  onCancel: () => void;
  onSubmit: () => void;
}) {
  const handleCancel = useModalFormCancel(onCancel);
  return (
    <>
      <button type="button" className="btn secondary" onClick={handleCancel}>
        {adminLabels.cancel}
      </button>
      <button type="button" className="btn primary" disabled={creating || !canSubmit} onClick={onSubmit}>
        {creating ? "…" : adminLabels.startBackup}
      </button>
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
    <Modal
      title={adminLabels.restoreDatabaseTitle}
      onClose={onCancel}
      footer={
        <>
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
        </>
      }
    >
      <div className="backup-restore-confirm">
        <p className={`text-danger${backup.database_key === "kyrox_core" ? " backup-restore-danger-banner" : ""}`}>
          {restoreWarningForDatabase(backup.database_key)}
        </p>
        {backup.database_key === "kyrox_core" && (
          <p className="text-danger">{adminLabels.restoreWarningKyroxCoreStrong}</p>
        )}
        <dl className="detail-list backup-restore-summary">
          <dt>{adminLabels.colDatabaseKey}</dt>
          <dd className="mono">{backup.database_key}</dd>
          <dt>{adminLabels.colDatabaseLabel}</dt>
          <dd>{backup.database_label ?? databaseKeyLabel(backup.database_key)}</dd>
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
          <TextInput
            id="restore-backup-confirm-text"
            type="text"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder={adminLabels.restoreConfirmPlaceholder}
            autoComplete="off"
            spellCheck={false}
          />
        </label>
        {error ? <FieldError>{error}</FieldError> : null}
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
    <Modal
      title={adminLabels.deleteBackupTitle}
      onClose={onCancel}
      footer={
        <>
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
        </>
      }
    >
      <div className="backup-delete-confirm">
        <p className="text-danger">{adminLabels.deleteBackupWarning}</p>
        <p>
          <strong>{adminLabels.colName}:</strong> {backup.file_name}
        </p>
        <label className="form-field">
          <span>{adminLabels.deleteConfirmLabel}</span>
          <TextInput
            id="delete-backup-confirm-text"
            type="text"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder={adminLabels.deleteConfirmPlaceholder}
            autoComplete="off"
            spellCheck={false}
          />
        </label>
        {error ? <FieldError>{error}</FieldError> : null}
      </div>
    </Modal>
  );
}

interface RestoreFromFileModalProps {
  notes: string;
  selectedFile: File | null;
  databaseKey: DatabaseKey;
  acknowledge: boolean;
  confirmText: string;
  restoring: boolean;
  error: string | null;
  onNotesChange: (value: string) => void;
  onFileChange: (file: File | null) => void;
  onDatabaseKeyChange: (value: DatabaseKey) => void;
  onAcknowledgeChange: (value: boolean) => void;
  onConfirmTextChange: (value: string) => void;
  onCancel: () => void;
  onSubmit: () => void;
}

function RestoreFromFileModal({
  notes,
  selectedFile,
  databaseKey,
  acknowledge,
  confirmText,
  restoring,
  error,
  onNotesChange,
  onFileChange,
  onDatabaseKeyChange,
  onAcknowledgeChange,
  onConfirmTextChange,
  onCancel,
  onSubmit,
}: RestoreFromFileModalProps) {
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const baseline = React.useMemo(
    () => ({ notes: "", acknowledge: false, confirmText: "", hasFile: false, databaseKey: "fair_crm" as DatabaseKey }),
    [],
  );
  useReportFormDirty(
    { notes, acknowledge, confirmText, hasFile: selectedFile != null, databaseKey },
    baseline,
  );
  const handleCancel = useModalFormCancel(onCancel);

  const canSubmit =
    selectedFile != null &&
    selectedFile.size > 0 &&
    selectedFile.name.toLowerCase().endsWith(".dump") &&
    acknowledge &&
    confirmText === RESTORE_CONFIRM_TEXT;

  return (
    <Modal
      title={adminLabels.restoreFromFileTitle}
      onClose={onCancel}
      className="modal-restore-from-file"
      footer={
        <>
          <button type="button" className="btn secondary" onClick={handleCancel} disabled={restoring}>
            {adminLabels.cancel}
          </button>
          <button
            type="button"
            className="btn danger backup-restore-upload-submit"
            disabled={restoring || !canSubmit}
            onClick={onSubmit}
          >
            {restoring ? "…" : adminLabels.restoreFromFileButton}
          </button>
        </>
      }
    >
      <div className="backup-restore-upload-modal">
        <Banner
          variant="error"
          className={`backup-restore-upload-warning${databaseKey === "kyrox_core" ? " backup-restore-danger-banner" : ""}`}
          role="alert"
        >
          <span className="backup-restore-upload-warning-icon" aria-hidden="true">
            !
          </span>
          <p>{restoreUploadWarningForDatabase(databaseKey)}</p>
        </Banner>

        <div className="field backup-restore-upload-database">
          <span className="field-label">{adminLabels.restoreUploadDatabaseLabel}</span>
          <div className="backup-database-options" role="radiogroup" aria-label={adminLabels.restoreUploadDatabaseLabel}>
            {DATABASE_KEY_OPTIONS.map((option) => {
              const selected = databaseKey === option.value;
              const inputId = `restore-upload-db-${option.value}`;
              return (
                <div
                  key={option.value}
                  className={`backup-database-option${selected ? " is-selected" : ""}`}
                >
                  <RadioField
                    id={inputId}
                    name="restore_upload_database_key"
                    label={option.title}
                    value={option.value}
                    checked={selected}
                    onChange={(value) => onDatabaseKeyChange(value as DatabaseKey)}
                    hideLabel
                    className="backup-database-option-control"
                  />
                  <label htmlFor={inputId} className="backup-database-option-title">
                    {option.title}
                  </label>
                  <span className="backup-database-option-desc field-hint">{option.description}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="field backup-restore-upload-file">
          <span className="field-label">{adminLabels.restoreUploadLabel}</span>
          <TextInput
            ref={fileInputRef}
            id="backup-restore-upload-file"
            type="file"
            accept=".dump"
            className="backup-restore-file-input"
            onChange={(e) => {
              const file = e.target.files?.[0] ?? null;
              onFileChange(file);
              if (file) {
                const inferred = inferDatabaseKeyFromFileName(file.name);
                if (inferred) {
                  onDatabaseKeyChange(inferred);
                }
              }
            }}
          />
          <div className="backup-restore-file-picker">
            <button
              type="button"
              className="btn secondary backup-restore-file-button"
              onClick={() => fileInputRef.current?.click()}
            >
              {adminLabels.restoreUploadPickButton}
            </button>
            <span
              className={`backup-restore-file-name${selectedFile ? "" : " is-empty"}`}
              title={selectedFile?.name ?? adminLabels.restoreUploadNoFileSelected}
            >
              {selectedFile?.name ?? adminLabels.restoreUploadNoFileSelected}
            </span>
          </div>
          <span className="field-hint">{adminLabels.restoreUploadHint}</span>
          {selectedFile && (
            <span className="field-hint">
              {adminLabels.restoreFileSizeLabel}: {formatBytes(selectedFile.size)}
            </span>
          )}
        </div>

        <label className="field backup-restore-upload-notes">
          <span className="field-label">{adminLabels.notesLabel}</span>
          <TextareaInput
            id="restore-upload-notes"
            rows={3}
            value={notes}
            onChange={(e) => onNotesChange(e.target.value)}
            placeholder={adminLabels.notesPlaceholder}
            maxLength={2000}
          />
        </label>

        <div className="restore-confirm-row">
          <CheckboxField
            id="restore-upload-acknowledge"
            label={adminLabels.restoreAcknowledge}
            checked={acknowledge}
            onChange={onAcknowledgeChange}
            hideLabel
            className="restore-confirm-row-control"
          />
          <label htmlFor="restore-upload-acknowledge">
            <span>{adminLabels.restoreAcknowledge}</span>
          </label>
        </div>

        <label className="field backup-restore-upload-confirm">
          <span className="field-label">{adminLabels.restoreConfirmLabel}</span>
          <TextInput
            id="restore-upload-confirm-text"
            type="text"
            value={confirmText}
            onChange={(e) => onConfirmTextChange(e.target.value)}
            placeholder={adminLabels.restoreConfirmPlaceholder}
            autoComplete="off"
            spellCheck={false}
          />
          <span className="field-hint">{adminLabels.restoreConfirmHelp}</span>
        </label>

        {error ? <FieldError>{error}</FieldError> : null}
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
  const [selectedDatabaseKeys, setSelectedDatabaseKeys] = React.useState<DatabaseKey[]>(["fair_crm"]);
  const [creating, setCreating] = React.useState(false);
  const [createError, setCreateError] = React.useState<string | null>(null);
  const [detailBackup, setDetailBackup] = React.useState<SystemBackup | null>(null);
  const [restoreTarget, setRestoreTarget] = React.useState<SystemBackup | null>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<SystemBackup | null>(null);
  const [showRestoreUploadModal, setShowRestoreUploadModal] = React.useState(false);
  const [restoreUploadNotes, setRestoreUploadNotes] = React.useState("");
  const [restoreUploadFile, setRestoreUploadFile] = React.useState<File | null>(null);
  const [restoreUploadDatabaseKey, setRestoreUploadDatabaseKey] = React.useState<DatabaseKey>("fair_crm");
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
    setSelectedDatabaseKeys(["fair_crm"]);
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
    setRestoreUploadDatabaseKey("fair_crm");
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
      const job = await restoreSystemBackupFromUpload(
        restoreUploadFile,
        restoreUploadDatabaseKey,
        restoreUploadNotes.trim() || null,
      );
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
    if (selectedDatabaseKeys.length === 0) {
      setCreateError(adminLabels.databaseKeysRequired);
      return;
    }
    setCreating(true);
    setNotice(null);
    setCreateError(null);
    try {
      const batch = await createSystemBackup(selectedDatabaseKeys, notes.trim() || null, backupFormat);
      setShowCreateModal(false);
      setNotes("");
      setSelectedDatabaseKeys(["fair_crm"]);
      setNotice(adminLabels.backupStarting);
      setPollingIds((prev) => {
        const next = new Set(prev);
        for (const item of batch.items) {
          next.add(item.id);
        }
        return next;
      });
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
    <PageShell>
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
      {restorePollError ? <Banner variant="error">{restorePollError}</Banner> : null}

      {activeTrackedJobs.length > 0 && (
        <div className="restore-job-polling-banner" aria-live="polite">
          <p className="text-muted">
            {activeTrackedJobs.some((job) => job.status === "running")
              ? adminLabels.restoreJobTrackingRunning
              : adminLabels.restoreJobTracking}
          </p>
          <ul className="restore-job-polling-list">
            {activeTrackedJobs.map((job) => (
              <li key={job.id}>
                <Badge variant={restoreJobStatusBadgeVariant(job.status)}>
                  {restoreJobStatusLabel(job.status)}
                </Badge>
                <span className="backup-file-name">{restoreJobFileLabel(job)}</span>
                {job.status === "manual_restore_required" && (
                  <span className="field-hint restore-job-queue-hint">
                    {adminLabels.restoreJobTrackingQueued.replace("{jobId}", job.id)}
                  </span>
                )}
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
          skeletonCols={9}
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
        <Modal
          title={adminLabels.newBackupTitle}
          onClose={closeCreateModal}
          size="md"
          className="modal-create-backup"
          footer={
            <CreateBackupModalFooter
              creating={creating}
              canSubmit={selectedDatabaseKeys.length > 0}
              onCancel={closeCreateModal}
              onSubmit={() => void handleCreateBackup()}
            />
          }
        >
          <CreateBackupModalContent
            notes={notes}
            onNotesChange={setNotes}
            backupFormat={backupFormat}
            onBackupFormatChange={setBackupFormat}
            selectedDatabaseKeys={selectedDatabaseKeys}
            onDatabaseKeysChange={setSelectedDatabaseKeys}
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
            <dt>{adminLabels.colDatabaseKey}</dt>
            <dd className="mono">{detailBackup.database_key}</dd>
            <dt>{adminLabels.colDatabaseLabel}</dt>
            <dd>{detailBackup.database_label ?? databaseKeyLabel(detailBackup.database_key)}</dd>
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
                <FieldError as="dd">{detailBackup.error_message}</FieldError>
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
        <RestoreJobDetailModal
          job={visibleDetailRestoreJob}
          onClose={closeRestoreJobDetailModal}
          onJobUpdated={(updated) => {
            if (detailRestoreJob?.id === updated.id) {
              setDetailRestoreJob(updated);
            }
            if (!isTerminalRestoreJobStatus(updated.status)) {
              trackRestoreJob(updated);
            }
          }}
        />
      )}

      {showRestoreUploadModal && (
        <RestoreFromFileModal
          notes={restoreUploadNotes}
          selectedFile={restoreUploadFile}
          databaseKey={restoreUploadDatabaseKey}
          acknowledge={restoreUploadAcknowledge}
          confirmText={restoreUploadConfirmText}
          restoring={restoring}
          error={restoreError}
          onNotesChange={setRestoreUploadNotes}
          onFileChange={setRestoreUploadFile}
          onDatabaseKeyChange={setRestoreUploadDatabaseKey}
          onAcknowledgeChange={setRestoreUploadAcknowledge}
          onConfirmTextChange={setRestoreUploadConfirmText}
          onCancel={closeRestoreUploadModal}
          onSubmit={() => void handleRestoreFromUpload()}
        />
      )}
    </PageShell>
  );
}

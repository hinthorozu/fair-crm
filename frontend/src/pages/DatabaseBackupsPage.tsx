import React from "react";
import {
  createSystemBackup,
  downloadSystemBackup,
  getSystemBackup,
  listSystemBackupsTable,
  ApiError,
} from "../api/systemAdmin";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { adminLabels } from "../labels/adminLabels";
import type { BackupFormat, SystemBackup } from "../types/systemBackup";
import type { BadgeVariant } from "../components/ui/Badge";

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

function formatLabel(format: BackupFormat): string {
  if (format === "postgresql_dump") return adminLabels.formatPostgresqlDumpShort;
  if (format === "postgresql_sql") return adminLabels.formatPostgresqlSqlShort;
  return adminLabels.formatUniversalPackageShort;
}

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
      render: (backup) => backup.file_name,
    },
    {
      key: "backup_format",
      title: adminLabels.colFormat,
      sortable: true,
      render: (backup) => formatLabel(backup.backup_format),
    },
    {
      key: "started_at",
      title: adminLabels.colCreatedAt,
      sortable: true,
      render: (backup) => new Date(backup.started_at).toLocaleString("tr-TR"),
    },
    {
      key: "created_by_email",
      title: adminLabels.colCreatedBy,
      sortable: true,
      render: (backup) => backup.created_by_email ?? backup.created_by.slice(0, 8),
    },
    {
      key: "file_size",
      title: adminLabels.colSize,
      sortable: true,
      render: (backup) => formatBytes(backup.file_size),
    },
    {
      key: "duration_seconds",
      title: adminLabels.colDuration,
      sortable: true,
      render: (backup) => formatDuration(backup.duration_seconds),
    },
    {
      key: "status",
      title: adminLabels.colStatus,
      sortable: true,
      render: (backup) => (
        <>
          <Badge variant={statusBadgeVariant(backup.status)}>{statusLabel(backup.status)}</Badge>
          {backup.status === "running" && (
            <div className="backup-progress-hint">{stageLabel(backup.progress_stage)}</div>
          )}
        </>
      ),
    },
    {
      key: "notes",
      title: adminLabels.colNotes,
      sortable: true,
      render: (backup) => backup.notes ?? "—",
    },
    {
      key: "actions",
      title: adminLabels.colActions,
      sortable: false,
      render: (backup) => (
        <div className="table-actions">
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
          <button type="button" className="btn link disabled-action" disabled title={adminLabels.restoreDisabledHint}>
            {adminLabels.actionRestore}
          </button>
          <button type="button" className="btn link disabled-action" disabled title={adminLabels.deleteDisabledHint}>
            {adminLabels.actionDelete}
          </button>
        </div>
      ),
    },
  ];
}

export function DatabaseBackupsPage() {
  const table = useServerDataTable<SystemBackup>({
    fetchFn: listSystemBackupsTable,
    defaultSort: { field: "started_at", direction: "desc" },
    pageSize: 50,
    urlSync: true,
    urlPath: "/admin/system/backups",
  });

  const [notice, setNotice] = React.useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = React.useState(false);
  const [notes, setNotes] = React.useState("");
  const [backupFormat, setBackupFormat] = React.useState<BackupFormat>("postgresql_dump");
  const [creating, setCreating] = React.useState(false);
  const [createError, setCreateError] = React.useState<string | null>(null);
  const [detailBackup, setDetailBackup] = React.useState<SystemBackup | null>(null);
  const [pollingIds, setPollingIds] = React.useState<Set<string>>(new Set());
  const [downloadingId, setDownloadingId] = React.useState<string | null>(null);

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
  }, [pollingIds, table]);

  const closeCreateModal = React.useCallback(() => {
    setShowCreateModal(false);
    setBackupFormat("postgresql_dump");
  }, []);

  const closeDetailModal = React.useCallback(() => setDetailBackup(null), []);

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

  const columns = React.useMemo(
    () =>
      buildBackupColumns({
        onDownload: handleDownload,
        onDetails: openDetails,
        downloadingId,
      }),
    [downloadingId],
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
        ]}
      />

      {notice && <p className="text-muted">{notice}</p>}

      <UniversalDataTable
        table={table}
        columns={columns}
        rowKey={(backup) => backup.id}
        skeletonCols={9}
        emptyState={
          <EmptyState title={adminLabels.backupsEmpty} description={adminLabels.backupsEmptyDescription} />
        }
      />

      {showCreateModal && (
        <Modal title={adminLabels.newBackupTitle} onClose={closeCreateModal}>
          <fieldset className="backup-format-options">
            <legend>{adminLabels.formatLabel}</legend>
            <label className="backup-format-option">
              <input
                type="radio"
                name="backup_format"
                value="postgresql_dump"
                checked={backupFormat === "postgresql_dump"}
                onChange={() => setBackupFormat("postgresql_dump")}
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
                onChange={() => setBackupFormat("postgresql_sql")}
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
                onChange={() => setBackupFormat("universal_data_package")}
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
              onChange={(e) => setNotes(e.target.value)}
              placeholder={adminLabels.notesPlaceholder}
              maxLength={2000}
            />
          </label>
          <p className="text-muted">{adminLabels.notesHint}</p>
          {createError && <p className="form-error">{createError}</p>}
          <div className="modal-actions">
            <button type="button" className="btn secondary" onClick={closeCreateModal}>
              {adminLabels.cancel}
            </button>
            <button type="button" className="btn primary" disabled={creating} onClick={() => void handleCreateBackup()}>
              {creating ? "…" : adminLabels.startBackup}
            </button>
          </div>
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
        </Modal>
      )}
    </div>
  );
}

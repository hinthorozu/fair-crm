import React from "react";
import {
  downloadDataOperationFile,
  getDataOperationRun,
  listDataOperations,
  runDataOperation,
  ApiError,
} from "../api/dataOperations";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import { adminLabels } from "../labels/adminLabels";
import type { DataOperationDefinition, DataOperationRun, DuplicateGroupByField } from "../types/dataOperations";
import type { BadgeVariant } from "../components/ui/Badge";

const POLL_INTERVAL_MS = 2000;

function formatDateTime(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

function statusLabel(status: DataOperationRun["status"]): string {
  if (status === "queued") return adminLabels.dataOpStatusQueued;
  if (status === "running") return adminLabels.dataOpStatusRunning;
  if (status === "completed") return adminLabels.dataOpStatusCompleted;
  return adminLabels.dataOpStatusFailed;
}

function statusBadgeVariant(status: DataOperationRun["status"]): BadgeVariant {
  if (status === "queued" || status === "running") return "info";
  if (status === "completed") return "success";
  return "danger";
}

function resultLabel(result: DataOperationRun["result"]): string {
  if (result === "success") return adminLabels.dataOpResultSuccess;
  if (result === "failed") return adminLabels.dataOpResultFailed;
  return "—";
}

function currentRun(operation: DataOperationDefinition): DataOperationRun | null {
  return operation.active_run ?? operation.last_run;
}

function isActive(run: DataOperationRun | null): boolean {
  return run?.status === "queued" || run?.status === "running";
}

interface DataOperationsPageProps {
  onOpenResult?: (runId: string, operationKey: string) => void;
}

const DUPLICATE_ANALYSIS_KEY = "duplicate_customer_analysis";

const DUPLICATE_GROUP_BY_OPTIONS: { value: DuplicateGroupByField; label: string }[] = [
  { value: "company_name", label: adminLabels.dataOpGroupByCompanyName },
  { value: "email", label: adminLabels.dataOpGroupByEmail },
  { value: "website", label: adminLabels.dataOpGroupByWebsite },
  { value: "phone", label: adminLabels.dataOpGroupByPhone },
];

export function DataOperationsPage({ onOpenResult }: DataOperationsPageProps) {
  const [operations, setOperations] = React.useState<DataOperationDefinition[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [runningKeys, setRunningKeys] = React.useState<Set<string>>(new Set());
  const [downloadingKey, setDownloadingKey] = React.useState<string | null>(null);
  const [duplicateGroupBy, setDuplicateGroupBy] = React.useState<DuplicateGroupByField>("company_name");

  const loadOperations = React.useCallback(async () => {
    try {
      const items = await listDataOperations();
      setOperations(items);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : adminLabels.dataOpLoadError);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadOperations();
  }, [loadOperations]);

  const activeRunIds = React.useMemo(() => {
    const ids = new Set<string>();
    for (const operation of operations) {
      if (operation.active_run && isActive(operation.active_run)) {
        ids.add(operation.active_run.id);
      }
    }
    return ids;
  }, [operations]);

  React.useEffect(() => {
    if (activeRunIds.size === 0) return undefined;

    const interval = window.setInterval(async () => {
      const updates = await Promise.all(
        Array.from(activeRunIds).map(async (runId) => {
          try {
            return await getDataOperationRun(runId);
          } catch {
            return null;
          }
        }),
      );

      const byId = new Map(updates.filter(Boolean).map((run) => [run!.id, run!]));
      if (byId.size === 0) return;

      setOperations((prev) =>
        prev.map((operation) => {
          const active = operation.active_run ? byId.get(operation.active_run.id) : null;
          if (!active) return operation;
          const finished = active.status === "completed" || active.status === "failed";
          const next = {
            ...operation,
            active_run: finished ? null : active,
            last_run: finished ? active : operation.last_run,
          };
          if (
            finished &&
            active.status === "completed" &&
            active.result === "success" &&
            operation.result_mode === "dataset" &&
            onOpenResult
          ) {
            onOpenResult(active.id, operation.key);
          }
          return next;
        }),
      );
    }, POLL_INTERVAL_MS);

    return () => window.clearInterval(interval);
  }, [activeRunIds, onOpenResult]);

  const handleRun = async (operation: DataOperationDefinition) => {
    if (operation.destructive) {
      const confirmed = window.confirm(adminLabels.dataOpDestructiveConfirm);
      if (!confirmed) return;
    }

    setRunningKeys((prev) => new Set(prev).add(operation.key));
    try {
      const payload =
        operation.key === DUPLICATE_ANALYSIS_KEY ? { group_by: duplicateGroupBy } : undefined;
      const started = await runDataOperation(operation.key, payload);
      const run = await getDataOperationRun(started.id);
      setOperations((prev) =>
        prev.map((item) =>
          item.key === operation.key
            ? {
                ...item,
                active_run: run,
              }
            : item,
        ),
      );
      if (
        run.status === "completed" &&
        run.result === "success" &&
        operation.result_mode === "dataset" &&
        onOpenResult
      ) {
        onOpenResult(run.id, operation.key);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : adminLabels.dataOpRunError);
    } finally {
      setRunningKeys((prev) => {
        const next = new Set(prev);
        next.delete(operation.key);
        return next;
      });
    }
  };

  const handleDownload = async (run: DataOperationRun, fileId: string, fileName: string) => {
    const key = `${run.id}:${fileId}`;
    setDownloadingKey(key);
    try {
      await downloadDataOperationFile(run.id, fileId, fileName);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : adminLabels.dataOpDownloadError);
    } finally {
      setDownloadingKey(null);
    }
  };

  return (
    <div className="data-operations-page">
      <PageHeader title={adminLabels.dataOperationsTitle} subtitle={adminLabels.dataOperationsSubtitle} />

      {error && <p className="text-danger">{error}</p>}
      {loading && <p className="text-muted">{adminLabels.dataOpLoading}</p>}

      {!loading && (
        <div className="data-operations-list">
          {operations.map((operation) => {
            const run = currentRun(operation);
            const busy =
              runningKeys.has(operation.key) || isActive(operation.active_run) || isActive(run);
            const downloadsFrom =
              operation.result_mode === "file" && run?.result === "success" ? run : operation.last_run;
            const datasetRun =
              operation.result_mode === "dataset" && operation.last_run?.result === "success"
                ? operation.last_run
                : null;

            return (
              <section key={operation.key} className="data-operation-card card">
                <div className="data-operation-card-header">
                  <div>
                    <h3>{operation.name}</h3>
                    <p className="text-muted">{operation.description}</p>
                    {operation.key === DUPLICATE_ANALYSIS_KEY && (
                      <fieldset className="data-operation-group-by">
                        <legend>{adminLabels.dataOpGroupByLabel}</legend>
                        <div className="data-operation-group-by-options">
                          {DUPLICATE_GROUP_BY_OPTIONS.map((option) => (
                            <label key={option.value} className="data-operation-group-by-option">
                              <input
                                type="radio"
                                name="duplicate-group-by"
                                value={option.value}
                                checked={duplicateGroupBy === option.value}
                                disabled={busy}
                                onChange={() => setDuplicateGroupBy(option.value)}
                              />
                              {option.label}
                            </label>
                          ))}
                        </div>
                      </fieldset>
                    )}
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={busy}
                    onClick={() => void handleRun(operation)}
                  >
                    {busy ? adminLabels.dataOpRunning : adminLabels.dataOpRun}
                  </button>
                </div>

                <dl className="data-operation-meta">
                  <div>
                    <dt>{adminLabels.dataOpColStatus}</dt>
                    <dd>
                      {run ? (
                        <Badge variant={statusBadgeVariant(run.status)}>{statusLabel(run.status)}</Badge>
                      ) : (
                        "—"
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt>{adminLabels.dataOpColStartedBy}</dt>
                    <dd>{run?.started_by_email ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>{adminLabels.dataOpColStartedAt}</dt>
                    <dd>{formatDateTime(run?.started_at ?? null)}</dd>
                  </div>
                  <div>
                    <dt>{adminLabels.dataOpColFinishedAt}</dt>
                    <dd>{formatDateTime(run?.completed_at ?? null)}</dd>
                  </div>
                  <div>
                    <dt>{adminLabels.dataOpColLastRun}</dt>
                    <dd>{formatDateTime(operation.last_run?.started_at ?? null)}</dd>
                  </div>
                  <div>
                    <dt>{adminLabels.dataOpColResult}</dt>
                    <dd>{resultLabel(run?.result ?? operation.last_run?.result ?? null)}</dd>
                  </div>
                </dl>

                {run?.error_message && <p className="text-danger">{run.error_message}</p>}

                {downloadsFrom?.output_files && downloadsFrom.output_files.length > 0 && (
                  <div className="data-operation-downloads">
                    <p className="data-operation-downloads-title">{adminLabels.dataOpDownloads}</p>
                    <ul>
                      {downloadsFrom.output_files.map((file) => {
                        const key = `${downloadsFrom.id}:${file.id}`;
                        return (
                          <li key={file.id}>
                            <button
                              type="button"
                              className="btn btn-link"
                              disabled={downloadingKey === key}
                              onClick={() => void handleDownload(downloadsFrom, file.id, file.file_name)}
                            >
                              {file.file_name}
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}

                {datasetRun && onOpenResult && (
                  <div className="data-operation-downloads">
                    <button
                      type="button"
                      className="btn btn-link"
                      onClick={() => onOpenResult(datasetRun.id, operation.key)}
                    >
                      {adminLabels.dataOpViewResults}
                    </button>
                  </div>
                )}
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

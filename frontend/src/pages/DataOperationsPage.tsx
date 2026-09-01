import React from "react";
import {
  downloadDataOperationFile,
  getDataOperationRun,
  listDataOperations,
  ApiError,
} from "../api/dataOperations";
import { createOperation } from "../api/operations";
import { FairEntitySelect } from "../components/FairEntitySelect";
import { PageHeader } from "../components/ui/PageHeader";
import { LoadingState } from "../components/ui/LoadingState";
import { Badge } from "../components/ui/Badge";
import { RadioField } from "../components/ui/form";
import { usePermissions } from "../hooks/usePermissions";
import { adminLabels } from "../labels/adminLabels";
import { operationLabels, operationTypeLabels } from "../labels/operationLabels";
import { PERMISSION_OPERATIONS_CREATE } from "../permissions/navigationPermissions";
import { OPERATION_EXECUTE } from "../permissions/operationPermissions";
import type { DataOperationDefinition, DataOperationRun, DuplicateGroupByField } from "../types/dataOperations";
import type { Operation } from "../types/operation";
import type { BadgeVariant } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { PageShell } from "../components/ui/PageShell";

const POLL_INTERVAL_MS = 2000;
const DATA_OPERATIONS_READ = "fair_crm.admin.data_operations.read";
const DATA_OPERATIONS_EXECUTE = "fair_crm.admin.data_operations.execute";

const duplicateCheckUiLabels = {
  run: "Çalıştır",
  running: "Çalışıyor…",
  loadError: "Duplicate kontrol işlemleri yüklenemedi.",
  runError: "İşlem başlatılamadı.",
  downloadError: "Dosya indirilemedi.",
  colStatus: "Çalışma Durumu",
  colStartedBy: "Başlatan",
  colStartedAt: "Başlangıç",
  colFinishedAt: "Bitiş",
  colLastRun: "Son Çalıştırma",
  colResult: "Sonuç",
  downloads: "İndirmeler",
  statusQueued: "Kuyrukta",
  statusRunning: "Çalışıyor",
  statusCompleted: "Tamamlandı",
  statusFailed: "Başarısız",
  resultSuccess: "Başarılı",
  resultFailed: "Başarısız",
  viewResults: "Sonuçları Gör",
} as const;

function formatDateTime(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

function statusLabel(status: DataOperationRun["status"]): string {
  if (status === "queued") return duplicateCheckUiLabels.statusQueued;
  if (status === "running") return duplicateCheckUiLabels.statusRunning;
  if (status === "completed") return duplicateCheckUiLabels.statusCompleted;
  return duplicateCheckUiLabels.statusFailed;
}

function statusBadgeVariant(status: DataOperationRun["status"]): BadgeVariant {
  if (status === "queued" || status === "running") return "info";
  if (status === "completed") return "success";
  return "danger";
}

function resultLabel(result: DataOperationRun["result"]): string {
  if (result === "success") return duplicateCheckUiLabels.resultSuccess;
  if (result === "failed") return duplicateCheckUiLabels.resultFailed;
  return "—";
}

function currentRun(operation: DataOperationDefinition): DataOperationRun | null {
  return operation.active_run ?? operation.last_run;
}

function isActive(run: DataOperationRun | null): boolean {
  return run?.status === "queued" || run?.status === "running";
}

function extractDataOperationRunId(operation: Operation): string | null {
  const result = operation.latest_run?.error_details?.result;
  if (!result || typeof result !== "object") return null;
  const raw = (result as { data_operation_run_id?: unknown }).data_operation_run_id;
  if (raw == null) return null;
  return String(raw);
}

interface DuplicateCheckOperationPageProps {
  onOpenResult?: (runId: string, operationKey: string) => void;
}

const DUPLICATE_ANALYSIS_KEY = "duplicate_customer_analysis";

const DUPLICATE_GROUP_BY_OPTIONS: { value: DuplicateGroupByField; label: string }[] = [
  { value: "company_name", label: adminLabels.dataOpGroupByCompanyName },
  { value: "email", label: adminLabels.dataOpGroupByEmail },
  { value: "website", label: adminLabels.dataOpGroupByWebsite },
  { value: "phone", label: adminLabels.dataOpGroupByPhone },
];

export function DuplicateCheckOperationPage({ onOpenResult }: DuplicateCheckOperationPageProps) {
  const { can } = usePermissions();
  const canRun = can(PERMISSION_OPERATIONS_CREATE) && can(OPERATION_EXECUTE);
  const canDownload = can(DATA_OPERATIONS_READ) && can(DATA_OPERATIONS_EXECUTE);
  const [operations, setOperations] = React.useState<DataOperationDefinition[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [runningKeys, setRunningKeys] = React.useState<Set<string>>(new Set());
  const [downloadingKey, setDownloadingKey] = React.useState<string | null>(null);
  const [duplicateGroupBy, setDuplicateGroupBy] = React.useState<DuplicateGroupByField>("company_name");
  const [duplicateFairId, setDuplicateFairId] = React.useState<string>("");

  const loadOperations = React.useCallback(async () => {
    try {
      const items = await listDataOperations();
      setOperations(items);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : duplicateCheckUiLabels.loadError);
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
    if (!canRun) return;
    if (operation.destructive) {
      const confirmed = window.confirm(adminLabels.dataOpDestructiveConfirm);
      if (!confirmed) return;
    }

    setRunningKeys((prev) => new Set(prev).add(operation.key));
    try {
      const typeConfig: Record<string, unknown> = { job_key: operation.key };
      if (operation.key === DUPLICATE_ANALYSIS_KEY) {
        typeConfig.group_by = duplicateGroupBy;
        if (duplicateFairId) {
          typeConfig.fair_id = duplicateFairId;
        }
      }
      const startedOperation = await createOperation({
        operation_type: "duplicate_check",
        title: operation.name,
        description: operation.description,
        source_kind: "none",
        type_config: typeConfig,
        start_immediately: true,
      });
      const dataRunId = extractDataOperationRunId(startedOperation);
      if (!dataRunId) {
        throw new Error(duplicateCheckUiLabels.runError);
      }
      const run = await getDataOperationRun(dataRunId);
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
      void loadOperations();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : duplicateCheckUiLabels.runError);
    } finally {
      setRunningKeys((prev) => {
        const next = new Set(prev);
        next.delete(operation.key);
        return next;
      });
    }
  };

  const handleDownload = async (run: DataOperationRun, fileId: string, fileName: string) => {
    if (!canDownload) return;
    const key = `${run.id}:${fileId}`;
    setDownloadingKey(key);
    try {
      await downloadDataOperationFile(run.id, fileId, fileName);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : duplicateCheckUiLabels.downloadError);
    } finally {
      setDownloadingKey(null);
    }
  };

  return (
    <PageShell className="data-operations-page">
      <PageHeader
        title={operationTypeLabels.duplicate_check}
        subtitle={operationLabels.duplicateCheckSubtitle}
      />

      {error && <p className="text-danger">{error}</p>}
      {loading && <LoadingState />}

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
              <Card as="section" padding="none" className="data-operation-card" key={operation.key}>
                <div className="data-operation-card-header">
                  <div>
                    <h3>{operation.name}</h3>
                    <p className="text-muted">{operation.description}</p>
                    {operation.key === DUPLICATE_ANALYSIS_KEY && (
                      <div className="data-operation-duplicate-filters">
                        <fieldset className="data-operation-group-by">
                          <legend>{adminLabels.dataOpGroupByLabel}</legend>
                          <div className="data-operation-group-by-options">
                            {DUPLICATE_GROUP_BY_OPTIONS.map((option) => (
                              <RadioField
                                key={option.value}
                                id={`duplicate-group-by-${option.value}`}
                                name="duplicate-group-by"
                                label={option.label}
                                value={option.value}
                                checked={duplicateGroupBy === option.value}
                                disabled={busy}
                                onChange={(value) => setDuplicateGroupBy(value as DuplicateGroupByField)}
                                className="data-operation-group-by-option"
                              />
                            ))}
                          </div>
                        </fieldset>
                        <div className="data-operation-fair-filter">
                          <label htmlFor="duplicate-fair-filter">{adminLabels.dataOpFairFilterLabel}</label>
                          <FairEntitySelect
                            id="duplicate-fair-filter"
                            value={duplicateFairId}
                            onChange={setDuplicateFairId}
                            disabled={busy}
                            allowClear
                            placeholder={adminLabels.dataOpFairFilterAll}
                            clearOptionLabel={adminLabels.dataOpFairFilterAll}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                  {canRun ? (
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={busy}
                      onClick={() => void handleRun(operation)}
                    >
                      {busy ? duplicateCheckUiLabels.running : duplicateCheckUiLabels.run}
                    </button>
                  ) : null}
                </div>

                <dl className="data-operation-meta">
                  <div>
                    <dt>{duplicateCheckUiLabels.colStatus}</dt>
                    <dd>
                      {run ? (
                        <Badge variant={statusBadgeVariant(run.status)}>{statusLabel(run.status)}</Badge>
                      ) : (
                        "—"
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt>{duplicateCheckUiLabels.colStartedBy}</dt>
                    <dd>{run?.started_by_email ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>{duplicateCheckUiLabels.colStartedAt}</dt>
                    <dd>{formatDateTime(run?.started_at ?? null)}</dd>
                  </div>
                  <div>
                    <dt>{duplicateCheckUiLabels.colFinishedAt}</dt>
                    <dd>{formatDateTime(run?.completed_at ?? null)}</dd>
                  </div>
                  <div>
                    <dt>{duplicateCheckUiLabels.colLastRun}</dt>
                    <dd>{formatDateTime(operation.last_run?.started_at ?? null)}</dd>
                  </div>
                  <div>
                    <dt>{duplicateCheckUiLabels.colResult}</dt>
                    <dd>{resultLabel(run?.result ?? operation.last_run?.result ?? null)}</dd>
                  </div>
                </dl>

                {run?.error_message && <p className="text-danger">{run.error_message}</p>}

                {canDownload && downloadsFrom?.output_files && downloadsFrom.output_files.length > 0 && (
                  <div className="data-operation-downloads">
                    <p className="data-operation-downloads-title">{duplicateCheckUiLabels.downloads}</p>
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
                      {duplicateCheckUiLabels.viewResults}
                    </button>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </PageShell>
  );
}

export const DataOperationsPage = DuplicateCheckOperationPage;

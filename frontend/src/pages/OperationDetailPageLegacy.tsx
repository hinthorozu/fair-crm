import React from "react";
import {
  downloadBulkEmailOperationExport,
  listBulkEmailOperationLogs,
  openBulkEmailOperationExport,
  retryBulkEmailOperationFailed,
} from "../api/bulkEmailOperation";
import { cancelOperation, getOperation, startOperation } from "../api/operations";
import { getFair } from "../api/fairs";
import { getAdapter } from "../api/scraper";
import { getTodo } from "../api/todos";
import { ApiError } from "../api/client";
import { AdapterRunLogConsole } from "../components/scraper/AdapterRunLogConsole";
import { EnrichmentRunDetailPanel } from "../components/scraper/EnrichmentRunDetailPanel";
import { BulkEmailOperationResultsTable } from "../components/operations/BulkEmailOperationResultsTable";
import { OperationRunStatusBadge } from "../components/operations/OperationRunStatusBadge";
import { Banner } from "../components/ui/Banner";
import { Badge, type BadgeVariant } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { LoadingState } from "../components/ui/LoadingState";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import type { BulkEmailOperationLogLine } from "../types/bulkEmailOperation";
import {
  operationLabels,
  operationPriorityLabels,
  operationTypeLabels,
  sourceKindLabels,
} from "../labels/operationLabels";
import { scraperLabels } from "../labels/scraperLabels";
import { todoPriorityLabels, todoStatusLabels } from "../labels/todoLabels";
import type {
  OperationDetail,
  OperationRun,
  OperationType,
  SourceKind,
} from "../types/operation";
import type { Todo, TodoPriority, TodoStatus } from "../types/todo";
import { getOutputFieldLabel } from "../utils/outputFieldDefinitions";
import type { RequestedOutputField } from "../types/scraper";
import {
  extractScraperResult,
  resolveOperationLiveLogTarget,
} from "../utils/operationScraperRun";
import { resolveRunUserFacingStatus } from "../utils/operationRunStatus";
import {
  buildEnrichmentSourceFilterRows,
  extractEnrichmentFairIds,
} from "../utils/enrichmentOperationSource";
import {
  extractOperationFairIds,
  formatOperationFairSourceLabel,
} from "../utils/operationFairSource";

interface OperationDetailPageProps {
  operationId: string;
  onBack: () => void;
  onOpenTodo?: (todoId: string) => void;
  onOpenImportBatch?: (batchId: string) => void;
}

function statusBadgeVariant(status: string): BadgeVariant {
  switch (status) {
    case "active":
    case "running":
    case "in_progress":
      return "info";
    case "completed":
    case "done":
      return "success";
    case "failed":
      return "danger";
    case "cancelled":
      return "neutral";
    case "paused":
    case "queued":
    case "ready":
    case "todo":
      return "warning";
    default:
      return "neutral";
  }
}

function formatRequestedFields(value: unknown): string | null {
  if (!Array.isArray(value) || value.length === 0) return null;
  const labels = value
    .filter((field): field is string => typeof field === "string" && field.trim().length > 0)
    .map((field) => getOutputFieldLabel(field as RequestedOutputField));
  return labels.length > 0 ? labels.join(", ") : null;
}

function isNonEmptyScraperConfig(value: unknown): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    Object.keys(value as Record<string, unknown>).length > 0
  );
}

const POLL_INTERVAL_MS = 10000;

export function OperationDetailPage({
  operationId,
  onBack,
  onOpenTodo,
  onOpenImportBatch,
}: OperationDetailPageProps) {
  const [detail, setDetail] = React.useState<OperationDetail | null>(null);
  const [linkedTodo, setLinkedTodo] = React.useState<Todo | null>(null);
  const [linkedTodoError, setLinkedTodoError] = React.useState<string | null>(null);
  const [sourceFairName, setSourceFairName] = React.useState<string | null>(null);
  const [sourceFairResolveFailed, setSourceFairResolveFailed] = React.useState(false);
  const [enrichmentFairNames, setEnrichmentFairNames] = React.useState<string[]>([]);
  const [bulkEmailFairNames, setBulkEmailFairNames] = React.useState<string[]>([]);
  const [adapterDisplayName, setAdapterDisplayName] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [banner, setBanner] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [bulkRecipientsRefresh, setBulkRecipientsRefresh] = React.useState(0);
  const [bulkLogs, setBulkLogs] = React.useState<BulkEmailOperationLogLine[]>([]);
  const [bulkLogsError, setBulkLogsError] = React.useState<string | null>(null);
  const [bulkLogsLoading, setBulkLogsLoading] = React.useState(false);
  const bulkLogConsoleRef = React.useRef<HTMLDivElement>(null);
  const [retryConfirmOpen, setRetryConfirmOpen] = React.useState(false);
  const [retrying, setRetrying] = React.useState(false);
  const [exportBusy, setExportBusy] = React.useState<string | null>(null);

  const load = React.useCallback(
    async (options?: { silent?: boolean }) => {
      if (!options?.silent) {
        setLoading(true);
        setLinkedTodo(null);
        setLinkedTodoError(null);
      }
      setError(null);
      try {
        const nextDetail = await getOperation(operationId);
        setDetail(nextDetail);
        // The operation detail is enough to render the page. Optional linked
        // todo resolution must not keep the entire screen behind a spinner.
        if (!options?.silent) setLoading(false);
        const relatedTodoId = nextDetail.operation.related_todo_id;
        if (relatedTodoId && !options?.silent) {
          void getTodo(relatedTodoId)
            .then((todo) => setLinkedTodo(todo))
            .catch(() => setLinkedTodoError(operationLabels.linkedTodoMissing));
        } else if (!relatedTodoId) {
          setLinkedTodo(null);
          setLinkedTodoError(null);
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : operationLabels.loadError);
      } finally {
        if (!options?.silent) setLoading(false);
      }
    },
    [operationId],
  );

  React.useEffect(() => {
    void load();
  }, [load]);

  const scraperSourceFairId =
    detail?.operation.operation_type === "scraper" &&
    detail.operation.source_kind === "fair"
      ? detail.operation.source_ids?.[0] ?? null
      : null;

  React.useEffect(() => {
    if (!scraperSourceFairId) {
      setSourceFairName(null);
      setSourceFairResolveFailed(false);
      return;
    }
    let cancelled = false;
    setSourceFairName(null);
    setSourceFairResolveFailed(false);
    void getFair(scraperSourceFairId)
      .then((fair) => {
        if (!cancelled) {
          setSourceFairName(fair.name);
          setSourceFairResolveFailed(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSourceFairName(null);
          setSourceFairResolveFailed(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scraperSourceFairId]);

  const enrichmentFairIdsKey =
    detail?.operation.operation_type === "enrichment"
      ? extractEnrichmentFairIds(detail.operation).join("|")
      : "";

  const bulkEmailFairIdsKey =
    detail?.operation.operation_type === "bulk_email" &&
    detail.operation.source_kind === "fair"
      ? extractOperationFairIds(detail.operation).join("|")
      : "";

  React.useEffect(() => {
    if (!enrichmentFairIdsKey) {
      setEnrichmentFairNames([]);
      return;
    }
    const fairIds = enrichmentFairIdsKey.split("|").filter(Boolean);
    let cancelled = false;
    void Promise.all(
      fairIds.map((fairId) =>
        getFair(fairId)
          .then((fair) => ({ id: fairId, name: (fair.name || "").trim() || fairId }))
          .catch(() => ({ id: fairId, name: fairId })),
      ),
    ).then((resolved) => {
      if (cancelled) return;
      // Preserve persisted order from fairIds.
      const byId = new Map(resolved.map((item) => [item.id, item.name]));
      setEnrichmentFairNames(fairIds.map((id) => byId.get(id) || id));
    });
    return () => {
      cancelled = true;
    };
  }, [enrichmentFairIdsKey]);

  React.useEffect(() => {
    if (!bulkEmailFairIdsKey) {
      setBulkEmailFairNames([]);
      return;
    }
    const fairIds = bulkEmailFairIdsKey.split("|").filter(Boolean);
    let cancelled = false;
    void Promise.all(
      fairIds.map((fairId) =>
        getFair(fairId)
          .then((fair) => ({ id: fairId, name: (fair.name || "").trim() }))
          .catch(() => ({ id: fairId, name: "" })),
      ),
    ).then((resolved) => {
      if (cancelled) return;
      const byId = new Map(resolved.map((item) => [item.id, item.name]));
      // Empty string when getFair fails — format helper then uses Fuar (n) fallback.
      setBulkEmailFairNames(fairIds.map((id) => byId.get(id) || ""));
    });
    return () => {
      cancelled = true;
    };
  }, [bulkEmailFairIdsKey]);

  const scraperAdapterKey =
    detail?.operation.operation_type === "scraper" &&
    typeof detail.operation.type_config?.adapter_key === "string"
      ? detail.operation.type_config.adapter_key.trim() || null
      : null;

  React.useEffect(() => {
    if (!scraperAdapterKey) {
      setAdapterDisplayName(null);
      return;
    }
    let cancelled = false;
    setAdapterDisplayName(null);
    void getAdapter(scraperAdapterKey)
      .then((adapter) => {
        if (!cancelled) {
          // AdapterDetail.name is the registry/API display name (not adapter_key).
          const name = (adapter.name || "").trim();
          setAdapterDisplayName(name || null);
        }
      })
      .catch(() => {
        if (!cancelled) setAdapterDisplayName(null);
      });
    return () => {
      cancelled = true;
    };
  }, [scraperAdapterKey]);

  const latestStatus =
    detail?.operation.latest_run?.status ?? detail?.runs[0]?.status ?? null;
  const shouldPoll = latestStatus === "queued" || latestStatus === "running";
  const isBulkEmailOp = detail?.operation.operation_type === "bulk_email";

  const loadBulkEmailExtras = React.useCallback(
    async (options?: { silent?: boolean; includeLogs?: boolean }) => {
      if (!isBulkEmailOp) return;
      const includeLogs = options?.includeLogs !== false;
      if (!options?.silent) {
        setBulkLogsLoading(true);
      }
      setBulkLogsError(null);
      const [, logsResult] = await Promise.allSettled([
        Promise.resolve(null),
        includeLogs ? listBulkEmailOperationLogs(operationId) : Promise.resolve(null),
      ]);
      if (includeLogs && logsResult.status === "fulfilled" && logsResult.value) {
        const incoming = logsResult.value.items;
        setBulkLogs(incoming);
      } else if (includeLogs && logsResult.status === "rejected") {
        const err = logsResult.reason;
        if (err instanceof ApiError && err.status === 404) {
          if (!options?.silent) {
            setBulkLogs([]);
          }
          setBulkLogsError(null);
        } else {
          setBulkLogsError(
            err instanceof ApiError ? err.message : operationLabels.bulkEmailLogsLoadError,
          );
        }
      }
      if (!options?.silent) {
        setBulkLogsLoading(false);
      }
    },
    [isBulkEmailOp, operationId],
  );

  React.useEffect(() => {
    // Refresh only while the operation is queued/running. Paused and terminal
    // operations remain stable until the page is opened again.
    if (!shouldPoll) return;
    const timer = window.setInterval(() => {
      if (shouldPoll) {
        void load({ silent: true });
      }
      if (isBulkEmailOp) {
        void loadBulkEmailExtras({ silent: true });
      }
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [shouldPoll, load, isBulkEmailOp, loadBulkEmailExtras]);

  React.useEffect(() => {
    if (!isBulkEmailOp) {
      setBulkLogs([]);
      setBulkLogsError(null);
      return;
    }
    void loadBulkEmailExtras();
  }, [isBulkEmailOp, loadBulkEmailExtras]);

  React.useEffect(() => {
    if (!bulkLogConsoleRef.current) return;
    bulkLogConsoleRef.current.scrollTop = bulkLogConsoleRef.current.scrollHeight;
  }, [bulkLogs]);

  const handleStart = async () => {
    setBusy(true);
    setBanner(null);
    try {
      await startOperation(operationId);
      setBanner(operationLabels.startSuccess);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : operationLabels.loadError);
    } finally {
      setBusy(false);
    }
  };

  const handleCancel = async () => {
    setBusy(true);
    setBanner(null);
    try {
      await cancelOperation(operationId);
      setBanner(operationLabels.cancelSuccess);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : operationLabels.loadError);
    } finally {
      setBusy(false);
    }
  };

  const handleRetryFailed = async () => {
    setRetrying(true);
    setBanner(null);
    setError(null);
    try {
      await retryBulkEmailOperationFailed(operationId);
      setRetryConfirmOpen(false);
      setBanner(operationLabels.bulkEmailRetrySuccess);
      await load();
      await loadBulkEmailExtras();
      setBulkRecipientsRefresh((value) => value + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : operationLabels.loadError);
      setRetryConfirmOpen(false);
    } finally {
      setRetrying(false);
    }
  };

  const handleBulkExport = async (
    format: "json" | "excel",
    mode: "download" | "open",
  ) => {
    const key = `${mode}-${format}`;
    setExportBusy(key);
    setError(null);
    try {
      if (mode === "download") {
        await downloadBulkEmailOperationExport(operationId, format);
      } else {
        await openBulkEmailOperationExport(operationId, format);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : operationLabels.bulkEmailExportError);
    } finally {
      setExportBusy(null);
    }
  };

  const runColumns = React.useMemo<UniversalDataTableColumn<OperationRun>[]>(
    () => [
      {
        key: "attempt",
        title: "Deneme",
        sortable: false,
        render: (item) => String(item.attempt),
      },
      {
        key: "status",
        title: operationLabels.colStatus,
        sortable: false,
        render: (item) => (
          <OperationRunStatusBadge status={resolveRunUserFacingStatus(item)} />
        ),
      },
      {
        key: "progress",
        title: operationLabels.colProgress,
        sortable: false,
        render: (item) =>
          `${Math.round((item.progress ?? 0) * 100)}% (${item.processed_items}/${item.total_items})`,
      },
      {
        key: "succeeded_items",
        title: "Başarılı",
        sortable: false,
        render: (item) => String(item.succeeded_items),
      },
      {
        key: "failed_items",
        title: "Başarısız",
        sortable: false,
        render: (item) => String(item.failed_items),
      },
      {
        key: "started_at",
        title: "Başlangıç",
        sortable: false,
        render: (item) =>
          item.started_at ? new Date(item.started_at).toLocaleString("tr-TR") : "—",
      },
      {
        key: "finished_at",
        title: "Bitiş",
        sortable: false,
        render: (item) =>
          item.finished_at ? new Date(item.finished_at).toLocaleString("tr-TR") : "—",
      },
      {
        key: "error_message",
        title: "Hata",
        sortable: false,
        allowWrap: true,
        render: (item) => item.error_message ?? "—",
      },
    ],
    [],
  );

  if (loading) {
    return (
      <PageShell>
        <LoadingState />
      </PageShell>
    );
  }

  if (!detail) {
    return (
      <PageShell>
        <PageHeader
          title={operationLabels.detailTitle}
          breadcrumbs={[
            { label: operationLabels.pageTitle, onClick: onBack },
            { label: operationLabels.detailTitle, current: true },
          ]}
        />
        {error ? <Banner variant="error">{error}</Banner> : null}
      </PageShell>
    );
  }

  const { operation, runs } = detail;
  const latest = operation.latest_run ?? runs[0] ?? null;
  const isManualTask = operation.operation_type === "manual_task";
  const isScraper = operation.operation_type === "scraper";
  const isEnrichment = operation.operation_type === "enrichment";
  const isBulkEmail = operation.operation_type === "bulk_email";
  const latestRunActive = latest?.status === "queued" || latest?.status === "running";
  const canStart =
    ["draft", "ready", "active"].includes(operation.status) &&
    !(isManualTask && operation.related_todo_id) &&
    !latestRunActive;
  const canCancel =
    ["draft", "ready", "active"].includes(operation.status) ||
    ((isScraper || isEnrichment) && latestRunActive);
  const failedCount = latest?.failed_items ?? 0;
  const canRetryFailed =
    isBulkEmail &&
    !latestRunActive &&
    (Boolean(operation.capabilities?.supports_retry) || failedCount > 0);
  const progressPct = Math.round((latest?.progress ?? 0) * 100);
  const typeConfig = operation.type_config ?? {};
  const scraperResult = isScraper || isEnrichment ? extractScraperResult(latest) : null;
  const liveLogTarget = isScraper
    ? resolveOperationLiveLogTarget(latest, scraperAdapterKey)
    : null;
  const enrichmentRunId = isEnrichment ? scraperResult?.scraper_run_id?.trim() || "" : "";
  const enrichmentAdapterKey =
    (typeof typeConfig.adapter_key === "string" ? typeConfig.adapter_key.trim() : "") ||
    scraperResult?.adapter_key ||
    "";
  const enrichmentSourceRows = isEnrichment
    ? buildEnrichmentSourceFilterRows(operation, enrichmentFairNames)
    : [];
  const requestedFieldsSummary = formatRequestedFields(typeConfig.requested_fields);
  const sourceUrlSummary =
    typeof typeConfig.source_url === "string" ? typeConfig.source_url.trim() : "";

  return (
    <PageShell>
      <PageHeader
        title={operation.title}
        subtitle={operationLabels.detailSubtitle}
        breadcrumbs={[
          { label: operationLabels.pageTitle, onClick: onBack },
          { label: operation.title, current: true },
        ]}
        actions={
          <>
            {canStart ? (
              <button
                type="button"
                className="btn primary"
                disabled={busy}
                onClick={() => void handleStart()}
              >
                {operationLabels.actionStart}
              </button>
            ) : null}
            {canRetryFailed ? (
              <button
                type="button"
                className="btn"
                disabled={busy || retrying}
                onClick={() => setRetryConfirmOpen(true)}
              >
                {retrying
                  ? operationLabels.bulkEmailRetryRunning
                  : operationLabels.bulkEmailRetryFailed}
              </button>
            ) : null}
            {canCancel ? (
              <button
                type="button"
                className="btn danger"
                disabled={busy}
                onClick={() => void handleCancel()}
              >
                {operationLabels.actionCancel}
              </button>
            ) : null}
          </>
        }
      />

      {banner ? <Banner variant="success">{banner}</Banner> : null}
      {error ? <Banner variant="error">{error}</Banner> : null}

      <div className="stack gap-lg">
        <Card>
          <div className="stack gap-md">
            <div className="row gap-sm" style={{ flexWrap: "wrap" }}>
              <OperationRunStatusBadge
                status={resolveRunUserFacingStatus(latest, operation.run_settings)}
              />
              <Badge variant="neutral">
                {operationTypeLabels[operation.operation_type as OperationType] ??
                  operation.operation_type}
              </Badge>
              <Badge variant="neutral">
                {operationPriorityLabels[
                  operation.priority as keyof typeof operationPriorityLabels
                ] ?? operation.priority}
              </Badge>
            </div>
            {operation.description ? <p className="text-muted">{operation.description}</p> : null}

            {isEnrichment && enrichmentSourceRows.length > 0 ? (
              <div className="stack gap-sm">
                <h3 className="section-title">{scraperLabels.enrichmentSourceSectionTitle}</h3>
                <dl className="detail-grid">
                  {enrichmentSourceRows.map((row) => (
                    <div key={row.key} className={row.values.length > 1 ? "full-width" : undefined}>
                      <dt>{row.label}</dt>
                      <dd>
                        {row.values.length <= 1 ? (
                          row.values[0] ?? "—"
                        ) : (
                          <ul className="selected-entity-list enrichment-source-fair-list">
                            {row.values.map((value) => (
                              <li key={`${row.key}:${value}`}>{value}</li>
                            ))}
                          </ul>
                        )}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            ) : null}

            <dl className="detail-grid">
              {!isEnrichment ? (
                <div>
                  <dt>{scraperLabels.enrichmentSourceSectionTitle}</dt>
                  <dd>
                    {isBulkEmail && operation.source_kind === "fair" ? (
                      formatOperationFairSourceLabel(
                        sourceKindLabels.fair,
                        bulkEmailFairNames,
                        extractOperationFairIds(operation).length,
                      )
                    ) : isScraper && operation.source_kind === "fair" ? (
                      sourceFairName ??
                      (sourceFairResolveFailed && scraperSourceFairId
                        ? scraperSourceFairId
                        : "—")
                    ) : (
                      <>
                        {sourceKindLabels[operation.source_kind as SourceKind] ??
                          operation.source_kind}
                        {operation.source_kind === "fair" &&
                        (operation.source_ids?.length ?? 0) > 0
                          ? ` (${operation.source_ids.length})`
                          : ""}
                      </>
                    )}
                  </dd>
                </div>
              ) : null}
              <div>
                <dt>Oluşturma</dt>
                <dd>{new Date(operation.created_at).toLocaleString("tr-TR")}</dd>
              </div>
              <div>
                <dt>Güncelleme</dt>
                <dd>{new Date(operation.updated_at).toLocaleString("tr-TR")}</dd>
              </div>
            </dl>
          </div>
        </Card>

        {isScraper ? (
          <Card>
            <h3 className="section-title">{operationLabels.scraperConfigTitle}</h3>
            <dl className="detail-grid">
              {adapterDisplayName ? (
                <div>
                  <dt>{operationLabels.adapterKeyLabel}</dt>
                  <dd>{adapterDisplayName}</dd>
                </div>
              ) : null}
              {sourceUrlSummary ? (
                <div>
                  <dt>{operationLabels.fairSourceUrlLabel}</dt>
                  <dd>{sourceUrlSummary}</dd>
                </div>
              ) : null}
              {isNonEmptyScraperConfig(typeConfig.scraper_config) ? (
                <div className="full-width">
                  <dt>{operationLabels.fairScraperConfigLabel}</dt>
                  <dd className="detail-multiline">
                    <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
                      {JSON.stringify(typeConfig.scraper_config, null, 2)}
                    </pre>
                  </dd>
                </div>
              ) : null}
              {requestedFieldsSummary ? (
                <div className="full-width">
                  <dt>{operationLabels.requestedFieldsLabel}</dt>
                  <dd>{requestedFieldsSummary}</dd>
                </div>
              ) : null}
            </dl>
          </Card>
        ) : null}

        {isScraper ? (
          <Card>
            <h3 className="section-title">{operationLabels.linkedScraperRunTitle}</h3>
            {scraperResult ? (
              <div className="stack gap-sm">
                <dl className="detail-grid">
                  <div>
                    <dt>{operationLabels.linkedScraperRunId}</dt>
                    <dd>{scraperResult.scraper_run_id || "—"}</dd>
                  </div>
                  <div>
                    <dt>{operationLabels.linkedImportBatchId}</dt>
                    <dd>{scraperResult.import_batch_id || "—"}</dd>
                  </div>
                  <div>
                    <dt>{operationLabels.linkedTotalRows}</dt>
                    <dd>
                      {scraperResult.total_rows != null ? String(scraperResult.total_rows) : "—"}
                    </dd>
                  </div>
                  <div>
                    <dt>{operationLabels.linkedInputUrl}</dt>
                    <dd>{scraperResult.input_url || "—"}</dd>
                  </div>
                </dl>
                {scraperResult.import_batch_id && onOpenImportBatch ? (
                  <div>
                    <button
                      type="button"
                      className="btn"
                      onClick={() => onOpenImportBatch(scraperResult.import_batch_id!)}
                    >
                      {operationLabels.linkedImportBatchOpen}
                    </button>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="text-muted">{operationLabels.runsEmpty}</p>
            )}
          </Card>
        ) : null}

        {isEnrichment ? (
          <Card>
            <h3 className="section-title">{scraperLabels.enrichmentRunDetailTitle}</h3>
            {enrichmentRunId ? (
              <EnrichmentRunDetailPanel
                key={enrichmentRunId}
                runId={enrichmentRunId}
                adapterKey={enrichmentAdapterKey || undefined}
                onOpenImportBatch={onOpenImportBatch}
                showActions
              />
            ) : (
              <p className="text-muted">{operationLabels.linkedScraperRunMissing}</p>
            )}
          </Card>
        ) : null}

        {isManualTask ? (
          <Card>
            <h3 className="section-title">{operationLabels.linkedTodoTitle}</h3>
            {linkedTodo ? (
              <div className="stack gap-sm">
                <div className="row gap-sm" style={{ flexWrap: "wrap", alignItems: "center" }}>
                  <strong>{linkedTodo.title}</strong>
                  <Badge variant={statusBadgeVariant(linkedTodo.status)}>
                    {todoStatusLabels[linkedTodo.status as TodoStatus] ?? linkedTodo.status}
                  </Badge>
                  <Badge variant="neutral">
                    {todoPriorityLabels[linkedTodo.priority as TodoPriority] ??
                      linkedTodo.priority}
                  </Badge>
                </div>
                <p className="text-muted">
                  Deadline:{" "}
                  {linkedTodo.deadline
                    ? new Date(linkedTodo.deadline).toLocaleString("tr-TR")
                    : "—"}
                </p>
                {onOpenTodo ? (
                  <div>
                    <button
                      type="button"
                      className="btn"
                      onClick={() => onOpenTodo(linkedTodo.id)}
                    >
                      {operationLabels.linkedTodoOpen}
                    </button>
                  </div>
                ) : null}
              </div>
            ) : linkedTodoError ? (
              <Banner variant="error">{linkedTodoError}</Banner>
            ) : (
              <p className="text-muted">{operationLabels.linkedTodoEmpty}</p>
            )}
          </Card>
        ) : null}

        {!isEnrichment ? (
          <Card>
            <h3 className="section-title">{operationLabels.progressTitle}</h3>
            {latest ? (
              <div className="stack gap-sm">
                <div className="row gap-sm" style={{ flexWrap: "wrap" }}>
                  <OperationRunStatusBadge
                    status={resolveRunUserFacingStatus(latest, operation.run_settings)}
                  />
                  <span>
                    {progressPct}% — {latest.processed_items}/{latest.total_items}
                  </span>
                </div>
                <div
                  role="progressbar"
                  aria-valuenow={progressPct}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  style={{
                    height: 8,
                    borderRadius: 999,
                    background: "var(--color-border, #ddd)",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${progressPct}%`,
                      height: "100%",
                      background: "var(--color-primary, #2563eb)",
                    }}
                  />
                </div>
                <p className="text-muted">
                  Başarılı: {latest.succeeded_items} · Başarısız: {latest.failed_items}
                </p>
              </div>
            ) : (
              <p className="text-muted">{operationLabels.runsEmpty}</p>
            )}
          </Card>
        ) : null}

        {isScraper ? (
          <Card>
            <h3 className="section-title">{operationLabels.liveLogTitle}</h3>
            {liveLogTarget ? (
              <AdapterRunLogConsole
                key={liveLogTarget.scraperRunId}
                adapterKey={liveLogTarget.adapterKey}
                focusRunId={liveLogTarget.scraperRunId}
                hideRunForm
              />
            ) : (
              <p className="text-muted">{operationLabels.linkedScraperRunMissing}</p>
            )}
          </Card>
        ) : null}

        {isBulkEmail ? (
          <Card>
            <h3 className="section-title">{operationLabels.bulkEmailLiveLogTitle}</h3>
            {bulkLogsError ? <Banner variant="error">{bulkLogsError}</Banner> : null}
            {bulkLogsLoading && bulkLogs.length === 0 ? <LoadingState variant="inline" /> : null}
            <div className="adapter-console-log" aria-live="polite" ref={bulkLogConsoleRef}>
              {bulkLogs.map((log) => (
                <div
                  key={
                    log.outbox_id
                      ? `outbox:${log.outbox_id}`
                      : [log.at ?? "", log.status ?? "", log.message].join("\u0001")
                  }
                  className={`adapter-console-line adapter-console-${log.level === "error" ? "error" : "info"}`}
                >
                  <div className="adapter-console-header">
                    <span className="adapter-console-time">
                      {log.at
                        ? new Date(log.at).toLocaleTimeString("tr-TR")
                        : "—"}
                    </span>
                    {log.status ? (
                      <span className="adapter-console-step">[{log.status}]</span>
                    ) : null}
                  </div>
                  <div className="adapter-console-message">{log.message}</div>
                </div>
              ))}
              {!bulkLogsLoading && bulkLogs.length === 0 && !bulkLogsError ? (
                <p className="text-muted">{operationLabels.bulkEmailLogsEmpty}</p>
              ) : null}
            </div>
          </Card>
        ) : null}

        {isBulkEmail ? (
          <Card>
            <div className="stack gap-sm">
              <div
                className="row gap-sm"
                style={{ flexWrap: "wrap", justifyContent: "space-between", alignItems: "center" }}
              >
                <h3 className="section-title" style={{ margin: 0 }}>
                  {operationLabels.bulkEmailResultsTitle}
                </h3>
                <div className="row gap-sm" style={{ flexWrap: "wrap" }}>
                  <button
                    type="button"
                    className="btn"
                    disabled={Boolean(exportBusy)}
                    onClick={() => void handleBulkExport("json", "download")}
                  >
                    {exportBusy === "download-json"
                      ? "…"
                      : operationLabels.bulkEmailExportJsonDownload}
                  </button>
                  <button
                    type="button"
                    className="btn"
                    disabled={Boolean(exportBusy)}
                    onClick={() => void handleBulkExport("json", "open")}
                  >
                    {exportBusy === "open-json" ? "…" : operationLabels.bulkEmailExportJsonOpen}
                  </button>
                  <button
                    type="button"
                    className="btn"
                    disabled={Boolean(exportBusy)}
                    onClick={() => void handleBulkExport("excel", "download")}
                  >
                    {exportBusy === "download-excel"
                      ? "…"
                      : operationLabels.bulkEmailExportExcelDownload}
                  </button>
                  <button
                    type="button"
                    className="btn"
                    disabled={Boolean(exportBusy)}
                    onClick={() => void handleBulkExport("excel", "open")}
                  >
                    {exportBusy === "open-excel" ? "…" : operationLabels.bulkEmailExportExcelOpen}
                  </button>
                </div>
              </div>
              <BulkEmailOperationResultsTable
                operationId={operationId}
                dataVersion={`${latest?.status ?? ""}:${latest?.processed_items ?? 0}:${latest?.succeeded_items ?? 0}:${latest?.failed_items ?? 0}:${bulkRecipientsRefresh}`}
              />
            </div>
          </Card>
        ) : null}

        <Card>
          <h3 className="section-title">{operationLabels.runsTitle}</h3>
          {runs.length === 0 ? (
            <EmptyState title={operationLabels.runsEmpty} />
          ) : (
            <UniversalDataTable
              columns={runColumns}
              items={runs}
              rowKey={(row) => row.id}
              loading={false}
            />
          )}
        </Card>
      </div>

      {retryConfirmOpen ? (
        <ConfirmDialog
          title={operationLabels.bulkEmailRetryFailed}
          message={operationLabels.bulkEmailRetryConfirm}
          confirmLabel={operationLabels.bulkEmailRetryFailed}
          loading={retrying}
          onConfirm={() => void handleRetryFailed()}
          onCancel={() => {
            if (retrying) return;
            setRetryConfirmOpen(false);
          }}
        />
      ) : null}
    </PageShell>
  );
}

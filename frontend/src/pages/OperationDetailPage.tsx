import React from "react";
import { cancelOperation, getOperation, startOperation } from "../api/operations";
import { getFair } from "../api/fairs";
import { getAdapter } from "../api/scraper";
import { getTodo } from "../api/todos";
import { ApiError } from "../api/client";
import { AdapterRunLogConsole } from "../components/scraper/AdapterRunLogConsole";
import { OperationRunStatusBadge } from "../components/operations/OperationRunStatusBadge";
import { Banner } from "../components/ui/Banner";
import { Badge, type BadgeVariant } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { LoadingState } from "../components/ui/LoadingState";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import {
  operationLabels,
  operationPriorityLabels,
  operationTypeLabels,
  sourceKindLabels,
} from "../labels/operationLabels";
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

const POLL_INTERVAL_MS = 3000;

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
  const [adapterDisplayName, setAdapterDisplayName] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [banner, setBanner] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

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
        const relatedTodoId = nextDetail.operation.related_todo_id;
        if (relatedTodoId && !options?.silent) {
          try {
            setLinkedTodo(await getTodo(relatedTodoId));
          } catch {
            setLinkedTodoError(operationLabels.linkedTodoMissing);
          }
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

  React.useEffect(() => {
    if (!shouldPoll) return;
    const timer = window.setInterval(() => {
      void load({ silent: true });
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [shouldPoll, load]);

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
  const latestRunActive = latest?.status === "queued" || latest?.status === "running";
  const canStart =
    ["draft", "ready", "active"].includes(operation.status) &&
    !(isManualTask && operation.related_todo_id) &&
    !latestRunActive;
  const canCancel =
    ["draft", "ready", "active"].includes(operation.status) ||
    (isScraper && latestRunActive);
  const progressPct = Math.round((latest?.progress ?? 0) * 100);
  const scraperResult = isScraper ? extractScraperResult(latest) : null;
  const liveLogTarget = isScraper
    ? resolveOperationLiveLogTarget(latest, scraperAdapterKey)
    : null;
  const typeConfig = operation.type_config ?? {};
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
            <dl className="detail-grid">
              <div>
                <dt>Kaynak</dt>
                <dd>
                  {isScraper && operation.source_kind === "fair" ? (
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
    </PageShell>
  );
}

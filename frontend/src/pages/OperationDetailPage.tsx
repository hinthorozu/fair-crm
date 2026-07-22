import React from "react";
import { cancelOperation, getOperation, startOperation } from "../api/operations";
import { getTodo } from "../api/todos";
import { ApiError } from "../api/client";
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
  operationStatusLabels,
  operationTypeLabels,
  runStatusLabels,
  sourceKindLabels,
} from "../labels/operationLabels";
import { todoPriorityLabels, todoStatusLabels } from "../labels/todoLabels";
import type {
  OperationDetail,
  OperationRun,
  OperationStatus,
  OperationType,
  RunStatus,
  SourceKind,
} from "../types/operation";
import type { Todo, TodoPriority, TodoStatus } from "../types/todo";

interface OperationDetailPageProps {
  operationId: string;
  onBack: () => void;
  onOpenTodo?: (todoId: string) => void;
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

export function OperationDetailPage({
  operationId,
  onBack,
  onOpenTodo,
}: OperationDetailPageProps) {
  const [detail, setDetail] = React.useState<OperationDetail | null>(null);
  const [linkedTodo, setLinkedTodo] = React.useState<Todo | null>(null);
  const [linkedTodoError, setLinkedTodoError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [banner, setBanner] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    setLinkedTodo(null);
    setLinkedTodoError(null);
    try {
      const nextDetail = await getOperation(operationId);
      setDetail(nextDetail);
      const relatedTodoId = nextDetail.operation.related_todo_id;
      if (relatedTodoId) {
        try {
          setLinkedTodo(await getTodo(relatedTodoId));
        } catch {
          setLinkedTodoError(operationLabels.linkedTodoMissing);
        }
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : operationLabels.loadError);
    } finally {
      setLoading(false);
    }
  }, [operationId]);

  React.useEffect(() => {
    void load();
  }, [load]);

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
          <Badge variant={statusBadgeVariant(item.status)}>
            {runStatusLabels[item.status as RunStatus] ?? item.status}
          </Badge>
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
  const canStart =
    Boolean(operation.capabilities.execution_ready) &&
    ["draft", "ready", "active"].includes(operation.status) &&
    !(isManualTask && operation.related_todo_id);
  const canCancel = ["draft", "ready", "active"].includes(operation.status);
  const progressPct = Math.round((latest?.progress ?? 0) * 100);

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
              <Badge variant={statusBadgeVariant(operation.status)}>
                {operationStatusLabels[operation.status as OperationStatus] ?? operation.status}
              </Badge>
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
                  {sourceKindLabels[operation.source_kind as SourceKind] ?? operation.source_kind}
                  {operation.source_kind === "fair" && (operation.source_ids?.length ?? 0) > 0
                    ? ` (${operation.source_ids.length})`
                    : ""}
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
                <Badge variant={statusBadgeVariant(latest.status)}>
                  {runStatusLabels[latest.status as RunStatus] ?? latest.status}
                </Badge>
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

        <Card>
          <h3 className="section-title">{operationLabels.capabilitiesTitle}</h3>
          <ul>
            {Object.entries(operation.capabilities).map(([key, value]) => (
              <li key={key}>
                {key}: {value ? "evet" : "hayır"}
              </li>
            ))}
          </ul>
        </Card>

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

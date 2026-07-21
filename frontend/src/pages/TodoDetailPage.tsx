import React from "react";
import { getTodo } from "../api/todos";
import {
  getTodoWorklistModalContext,
  getTodoWorklistProgress,
  listTodoWorklist,
  recordTodoWorklistActivity,
} from "../api/todoWorklist";
import { ApiError } from "../api/client";
import { TodoWorklistActivityModal } from "../components/todos/TodoWorklistActivityModal";
import { LoadingState } from "../components/ui/LoadingState";
import { PageHeader } from "../components/ui/PageHeader";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { FilterPanel } from "../components/ui/FilterPanel";
import { TextInput } from "../components/ui/form";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { todoLabels } from "../labels/todoLabels";
import { labels } from "../labels";
import {
  todoWorklistLabels,
  worklistFilterOptions,
  worklistStatusBadgeVariant,
  worklistStatusLabels,
} from "../labels/todoWorklistLabels";
import type { Todo } from "../types/todo";
import { Banner } from "../components/ui/Banner";
import { TableEntityLink } from "../components/ui/TableEntityLink";
import { PageShell } from "../components/ui/PageShell";
import type {
  RecordTodoWorklistActivityPayload,
  TodoWorklistModalContext,
  TodoWorklistProgress,
  TodoWorklistRow,
  WorklistFilter,
} from "../types/todoWorklist";

interface TodoDetailPageProps {
  todoId: string;
  onBack: () => void;
  onTodoLoaded?: (title: string) => void;
  onOpenCustomer?: (customerId: string) => void;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("tr-TR");
}

export function TodoDetailPage({
  todoId,
  onBack,
  onTodoLoaded,
  onOpenCustomer,
}: TodoDetailPageProps) {
  const [todo, setTodo] = React.useState<Todo | null>(null);
  const [loadingTodo, setLoadingTodo] = React.useState(true);
  const [todoError, setTodoError] = React.useState<string | null>(null);
  const [progress, setProgress] = React.useState<TodoWorklistProgress | null>(null);
  const [progressError, setProgressError] = React.useState<string | null>(null);
  const [activityModalOpen, setActivityModalOpen] = React.useState(false);
  const [selectedCustomerId, setSelectedCustomerId] = React.useState<string | null>(null);
  const [modalContext, setModalContext] = React.useState<TodoWorklistModalContext | null>(null);
  const [modalLoading, setModalLoading] = React.useState(false);
  const [saveError, setSaveError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [saveSuccess, setSaveSuccess] = React.useState<string | null>(null);

  const hasSourceFair = Boolean(todo?.source_fair_id);

  const table = useServerDataTable<TodoWorklistRow>({
    enabled: hasSourceFair,
    fetchFn: (params) =>
      listTodoWorklist(todoId, {
        page: params.page,
        pageSize: params.pageSize,
        search: params.search,
        sortBy: params.sortBy ?? undefined,
        sortOrder: params.sortOrder ?? undefined,
        filter: (params.filters.filter as WorklistFilter | undefined) ?? "yapilmadi",
      }),
    defaultSort: { field: "company_name", direction: "asc" },
    defaultFilters: { filter: "yapilmadi" },
    filterKeys: ["filter"],
    urlSync: true,
    urlPath: `/todos/${todoId}`,
  });

  const worklistFilter = (table.filters.filter as WorklistFilter | undefined) ?? "yapilmadi";

  const refreshProgress = React.useCallback(async () => {
    try {
      const next = await getTodoWorklistProgress(todoId);
      setProgress(next);
      setProgressError(null);
    } catch (err) {
      setProgressError(err instanceof ApiError ? err.message : todoWorklistLabels.loadError);
    }
  }, [todoId]);

  const loadModalContext = React.useCallback(
    async (customerId: string) => {
      setModalLoading(true);
      setSaveError(null);
      try {
        const context = await getTodoWorklistModalContext(todoId, customerId);
        setModalContext(context);
      } catch (err) {
        setModalContext(null);
        setSaveError(err instanceof ApiError ? err.message : todoWorklistLabels.loadError);
      } finally {
        setModalLoading(false);
      }
    },
    [todoId],
  );

  React.useEffect(() => {
    let cancelled = false;
    setLoadingTodo(true);
    getTodo(todoId)
      .then((loaded) => {
        if (cancelled) return;
        setTodo(loaded);
        setTodoError(null);
        onTodoLoaded?.(loaded.title);
      })
      .catch((err) => {
        if (cancelled) return;
        setTodo(null);
        setTodoError(err instanceof ApiError ? err.message : todoLabels.loadError);
      })
      .finally(() => {
        if (!cancelled) setLoadingTodo(false);
      });
    return () => {
      cancelled = true;
    };
  }, [todoId, onTodoLoaded]);

  React.useEffect(() => {
    if (!hasSourceFair) return;
    void refreshProgress();
  }, [hasSourceFair, refreshProgress]);

  const handleFilterChange = (filter: WorklistFilter) => {
    table.setFilter("filter", filter);
  };

  const closeActivityModal = React.useCallback(() => {
    setActivityModalOpen(false);
    setSelectedCustomerId(null);
    setModalContext(null);
    setSaveError(null);
  }, []);

  const handleOpenActivity = (row: TodoWorklistRow) => {
    setSelectedCustomerId(row.customer_id);
    setActivityModalOpen(true);
    setSaveSuccess(null);
    setSaveError(null);
    void loadModalContext(row.customer_id);
  };

  const handleSaveActivity = async (payload: RecordTodoWorklistActivityPayload) => {
    if (!selectedCustomerId) return;
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(null);
    try {
      const result = await recordTodoWorklistActivity(todoId, selectedCustomerId, payload);
      setProgress(result.progress);
      setSaveSuccess(todoWorklistLabels.saveSuccess);
      await table.refresh();
      await refreshProgress();

      if (payload.advance_to_next && result.next_customer_id) {
        setSelectedCustomerId(result.next_customer_id);
        await loadModalContext(result.next_customer_id);
      } else {
        closeActivityModal();
      }
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : todoWorklistLabels.saveError);
    } finally {
      setSaving(false);
    }
  };

  const columns = React.useMemo<UniversalDataTableColumn<TodoWorklistRow>[]>(
    () => [
      {
        key: "customer_name",
        title: todoWorklistLabels.colCustomer,
        sortField: "company_name",
        render: (row) => (
          <TableEntityLink onClick={() => handleOpenActivity(row)}>
            {row.customer_name}
          </TableEntityLink>
        ),
      },
      {
        key: "location",
        title: todoWorklistLabels.colCityCountry,
        render: (row) => [row.city, row.country].filter(Boolean).join(" / ") || "—",
      },
      {
        key: "phone_summary",
        title: todoWorklistLabels.colPhone,
        render: (row) => row.phone_summary || "—",
      },
      {
        key: "email_summary",
        title: todoWorklistLabels.colEmail,
        render: (row) => row.email_summary || "—",
      },
      {
        key: "last_outcome_name",
        title: todoWorklistLabels.colLastOutcome,
        render: (row) => row.last_outcome_name || "—",
      },
      {
        key: "last_note_summary",
        title: todoWorklistLabels.colLastNote,
        render: (row) => row.last_note_summary || "—",
      },
      {
        key: "follow_up_at",
        title: todoWorklistLabels.colFollowUp,
        sortField: "follow_up_at",
        render: (row) => formatDateTime(row.follow_up_at),
      },
      {
        key: "primary_status",
        title: todoWorklistLabels.colStatus,
        sortField: "primary_status",
        render: (row) => (
          <Badge variant={worklistStatusBadgeVariant(row.primary_status)}>
            {worklistStatusLabels[row.primary_status]}
          </Badge>
        ),
      },
      {
        key: "actions",
        title: todoWorklistLabels.colActions,
        sortable: false,
        className: "actions",
        render: (row) => (
          <button
            type="button"
            className="btn secondary small"
            onClick={() => onOpenCustomer?.(row.customer_id)}
          >
            {todoWorklistLabels.openCustomerCard}
          </button>
        ),
      },
    ],
    [onOpenCustomer, handleOpenActivity],
  );

  if (loadingTodo) {
    return <LoadingState />;
  }

  if (todoError || !todo) {
    return (
      <PageShell>
        <PageHeader title={todoLabels.pageTitle} />
        <Banner variant="error">{todoError ?? todoLabels.loadError}</Banner>
        <button type="button" className="btn secondary" onClick={onBack}>
          {todoWorklistLabels.backToList}
        </button>
      </PageShell>
    );
  }

  return (
    <PageShell className="todo-detail-page">
      <PageHeader
        title={todo.title}
        subtitle={todo.description || undefined}
        actions={[
          {
            label: todoWorklistLabels.backToList,
            onClick: onBack,
            variant: "secondary",
          },
        ]}
      />

      {hasSourceFair ? (
        <>
          {progress && (
            <Card className="todo-worklist-progress">
              <h3>{todoWorklistLabels.progressTitle}</h3>
              <div className="todo-worklist-progress-grid">
                <div>
                  <span className="muted">{todoWorklistLabels.progressTotal}</span>
                  <strong>{progress.total}</strong>
                </div>
                <div>
                  <span className="muted">{todoWorklistLabels.progressNotStarted}</span>
                  <strong>{progress.not_started}</strong>
                </div>
                <div>
                  <span className="muted">{todoWorklistLabels.progressInFollowUp}</span>
                  <strong>{progress.in_follow_up}</strong>
                </div>
                <div>
                  <span className="muted">{todoWorklistLabels.progressClosed}</span>
                  <strong>{progress.closed}</strong>
                </div>
              </div>
              {progressError ? <Banner variant="error">{progressError}</Banner> : null}
            </Card>
          )}

          <section className="todo-worklist-section">
            <h3>{todoWorklistLabels.worklistTitle}</h3>
            <div className="todo-worklist-segments">
              {worklistFilterOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={`btn ${worklistFilter === option.value ? "primary" : "secondary"}`}
                  onClick={() => handleFilterChange(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>

            <UniversalDataTable
              table={table}
              skeletonCols={9}
              toolbar={
                <FilterPanel
                  actions={
                    <button type="button" className="btn secondary" onClick={() => void table.refresh()}>
                      {labels.refresh}
                    </button>
                  }
                >
                  <TextInput
                    id="todo-worklist-search"
                    type="search"
                    className="search-input"
                    placeholder={todoLabels.searchPlaceholder}
                    value={table.search}
                    onChange={(e) => table.setSearch(e.target.value)}
                    aria-label={todoLabels.searchPlaceholder}
                  />
                </FilterPanel>
              }
              columns={columns}
              rowKey={(row) => row.customer_id}
              emptyState={<EmptyState title={todoWorklistLabels.emptyWorklist} />}
            />
          </section>

          {saveSuccess && <Banner variant="success">{saveSuccess}</Banner>}

          <TodoWorklistActivityModal
            open={activityModalOpen}
            context={modalContext}
            loading={modalLoading}
            saving={saving}
            error={saveError}
            onClose={closeActivityModal}
            onSave={handleSaveActivity}
          />
        </>
      ) : (
        <Card className="todo-worklist-missing-fair">
          <p>{todoWorklistLabels.missingSourceFair}</p>
          <p className="muted">{todoWorklistLabels.missingSourceFairAction}</p>
        </Card>
      )}
    </PageShell>
  );
}

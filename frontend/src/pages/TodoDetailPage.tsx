import React from "react";
import { getCustomer } from "../api/customers";
import { getFair } from "../api/fairs";
import { getTodo, updateTodo } from "../api/todos";
import {
  getTodoWorklistModalContext,
  getTodoWorklistProgress,
  listTodoWorklist,
  recordTodoWorklistActivity,
} from "../api/todoWorklist";
import { ApiError } from "../api/client";
import { CompleteTodoModal } from "../components/todos/CompleteTodoModal";
import {
  TODO_FORM_ID,
  TodoForm,
  canEditTodo,
  formValuesToUpdatePayload,
  todoToFormValues,
  type TodoFormValues,
} from "../components/todos/TodoForm";
import { TodoWorklistActivityModal } from "../components/todos/TodoWorklistActivityModal";
import { LoadingState } from "../components/ui/LoadingState";
import { PageHeader, type PageHeaderAction } from "../components/ui/PageHeader";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { Badge, type BadgeVariant } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { FilterPanel } from "../components/ui/FilterPanel";
import { FormModal, TextInput } from "../components/ui/form";
import { useServerDataTable } from "../hooks/useServerDataTable";
import {
  todoCategoryLabels,
  todoLabels,
  todoPriorityLabels,
  todoStatusLabels,
} from "../labels/todoLabels";
import { labels } from "../labels";
import {
  todoWorklistLabels,
  worklistFilterOptions,
  worklistStatusBadgeVariant,
  worklistStatusLabels,
} from "../labels/todoWorklistLabels";
import {
  canPerformTodoAction,
  getGrantedTodoPermissions,
} from "../permissions/todoPermissions";
import type { Todo, TodoPriority, TodoStatus } from "../types/todo";
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

function canCompleteTodo(todo: Todo): boolean {
  return todo.status !== "done" && todo.status !== "archived" && todo.status !== "cancelled";
}

function statusBadgeVariant(status: TodoStatus): BadgeVariant {
  switch (status) {
    case "done":
      return "success";
    case "in_progress":
      return "info";
    case "cancelled":
    case "archived":
      return "neutral";
    case "todo":
    default:
      return "default";
  }
}

function priorityBadgeVariant(priority: TodoPriority): BadgeVariant {
  switch (priority) {
    case "urgent":
      return "danger";
    case "high":
      return "warning";
    case "low":
      return "neutral";
    case "normal":
    default:
      return "default";
  }
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
  const [customerName, setCustomerName] = React.useState<string | null>(null);
  const [fairName, setFairName] = React.useState<string | null>(null);
  const [progress, setProgress] = React.useState<TodoWorklistProgress | null>(null);
  const [progressError, setProgressError] = React.useState<string | null>(null);
  const [activityModalOpen, setActivityModalOpen] = React.useState(false);
  const [selectedCustomerId, setSelectedCustomerId] = React.useState<string | null>(null);
  const [modalContext, setModalContext] = React.useState<TodoWorklistModalContext | null>(null);
  const [modalLoading, setModalLoading] = React.useState(false);
  const [saveError, setSaveError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [saveSuccess, setSaveSuccess] = React.useState<string | null>(null);
  const [completeModalOpen, setCompleteModalOpen] = React.useState(false);
  const [editOpen, setEditOpen] = React.useState(false);
  const [formSaving, setFormSaving] = React.useState(false);

  const grantedPermissions = React.useMemo(() => getGrantedTodoPermissions(), []);
  const canUpdate = canPerformTodoAction(grantedPermissions, "update");

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
    if (!todo?.customer_id) {
      setCustomerName(null);
      return;
    }
    let cancelled = false;
    void getCustomer(todo.customer_id)
      .then((customer) => {
        if (!cancelled) setCustomerName(customer.display_name);
      })
      .catch(() => {
        if (!cancelled) setCustomerName(null);
      });
    return () => {
      cancelled = true;
    };
  }, [todo?.customer_id]);

  React.useEffect(() => {
    if (!todo?.source_fair_id) {
      setFairName(null);
      return;
    }
    let cancelled = false;
    void getFair(todo.source_fair_id)
      .then((fair) => {
        if (!cancelled) setFairName(fair.name);
      })
      .catch(() => {
        if (!cancelled) setFairName(null);
      });
    return () => {
      cancelled = true;
    };
  }, [todo?.source_fair_id]);

  React.useEffect(() => {
    if (!hasSourceFair) {
      setProgress(null);
      setProgressError(null);
      return;
    }
    void refreshProgress();
  }, [hasSourceFair, refreshProgress]);

  React.useEffect(() => {
    if (!editOpen) setFormSaving(false);
  }, [editOpen]);

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

  const handleEditSubmit = async (values: TodoFormValues) => {
    const updated = await updateTodo(todoId, formValuesToUpdatePayload(values));
    setTodo(updated);
    setEditOpen(false);
    setSaveSuccess(todoLabels.updateSuccess);
    onTodoLoaded?.(updated.title);
    if (updated.source_fair_id) {
      await table.refresh();
      await refreshProgress();
    } else {
      setProgress(null);
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
    [onOpenCustomer],
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

  const headerActions: PageHeaderAction[] = [
    {
      id: "back",
      label: todoWorklistLabels.backToList,
      onClick: onBack,
      variant: "secondary",
    },
  ];
  if (canUpdate && canEditTodo(todo)) {
    headerActions.unshift({
      id: "edit",
      label: todoLabels.actionEdit,
      onClick: () => setEditOpen(true),
      variant: "secondary",
    });
  }
  if (canUpdate && canCompleteTodo(todo)) {
    headerActions.unshift({
      id: "complete",
      label: todoLabels.actionComplete,
      onClick: () => setCompleteModalOpen(true),
      variant: "primary",
    });
  }

  const customerDisplay = todo.customer_id
    ? customerName || todoLabels.fieldCustomerNone
    : todoLabels.fieldCustomerNone;
  const fairDisplay = todo.source_fair_id
    ? fairName || todoLabels.fieldSourceFairNone
    : todoLabels.fieldSourceFairNone;

  return (
    <PageShell className="todo-detail-page">
      <PageHeader title={todo.title} actions={headerActions} />

      {saveSuccess ? <Banner variant="success">{saveSuccess}</Banner> : null}

      <Card className="todo-detail-meta">
        <dl className="detail-grid todo-detail-meta-grid">
          <div>
            <dt>{todoLabels.fieldTitle}</dt>
            <dd>{todo.title}</dd>
          </div>
          <div>
            <dt>{todoLabels.fieldDescription}</dt>
            <dd>{todo.description?.trim() ? todo.description : "—"}</dd>
          </div>
          <div>
            <dt>{todoLabels.fieldStatus}</dt>
            <dd>
              <Badge variant={statusBadgeVariant(todo.status)}>
                {todoStatusLabels[todo.status]}
              </Badge>
              {todo.is_overdue ? (
                <>
                  {" "}
                  <Badge variant="danger">{todoLabels.overdueBadge}</Badge>
                </>
              ) : null}
            </dd>
          </div>
          <div>
            <dt>{todoLabels.fieldPriority}</dt>
            <dd>
              <Badge variant={priorityBadgeVariant(todo.priority)}>
                {todoPriorityLabels[todo.priority]}
              </Badge>
            </dd>
          </div>
          <div>
            <dt>{todoLabels.fieldCategory}</dt>
            <dd>{todoCategoryLabels[todo.category] ?? todo.category}</dd>
          </div>
          <div>
            <dt>{todoLabels.fieldDeadline}</dt>
            <dd>{formatDateTime(todo.deadline)}</dd>
          </div>
          <div>
            <dt>{todoLabels.fieldCustomer}</dt>
            <dd>
              {todo.customer_id && customerName && onOpenCustomer ? (
                <TableEntityLink onClick={() => onOpenCustomer(todo.customer_id!)}>
                  {customerName}
                </TableEntityLink>
              ) : (
                customerDisplay
              )}
            </dd>
          </div>
          <div>
            <dt>{todoLabels.fieldSourceFair}</dt>
            <dd>{fairDisplay}</dd>
          </div>
          <div>
            <dt>{todoLabels.fieldAssignee}</dt>
            <dd>{todo.assignee_user_id || "—"}</dd>
          </div>
          <div>
            <dt>{todoLabels.fieldCreatedAt}</dt>
            <dd>{formatDateTime(todo.created_at)}</dd>
          </div>
          <div>
            <dt>{todoLabels.fieldUpdatedAt}</dt>
            <dd>{formatDateTime(todo.updated_at)}</dd>
          </div>
          {todo.completed_at ? (
            <div>
              <dt>{todoLabels.fieldCompletedAt}</dt>
              <dd>{formatDateTime(todo.completed_at)}</dd>
            </div>
          ) : null}
        </dl>
      </Card>

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
      ) : null}

      {editOpen ? (
        <FormModal
          title={todoLabels.editTodo}
          onClose={() => setEditOpen(false)}
          size="lg"
          formWidth="standard"
          footer={
            <>
              <Button
                type="button"
                variant="secondary"
                onClick={() => setEditOpen(false)}
                disabled={formSaving}
              >
                {todoLabels.cancel}
              </Button>
              <Button type="submit" form={TODO_FORM_ID} variant="primary" loading={formSaving}>
                {formSaving ? todoLabels.saving : todoLabels.save}
              </Button>
            </>
          }
        >
          <TodoForm
            initial={todoToFormValues(todo)}
            onSubmit={handleEditSubmit}
            onSavingChange={setFormSaving}
          />
        </FormModal>
      ) : null}

      {completeModalOpen ? (
        <CompleteTodoModal
          todo={todo}
          onClose={() => setCompleteModalOpen(false)}
          onCompleted={(updated) => {
            setTodo(updated);
            setCompleteModalOpen(false);
            setSaveSuccess(todoLabels.completeSuccess);
            onTodoLoaded?.(updated.title);
          }}
        />
      ) : null}
    </PageShell>
  );
}

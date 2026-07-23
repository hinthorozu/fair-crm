import React from "react";
import {
  archiveTodo,
  createTodo,
  deleteTodo,
  listTodos,
  updateTodo,
} from "../api/todos";
import { ApiError } from "../api/client";
import { CompleteTodoModal } from "../components/todos/CompleteTodoModal";
import {
  TODO_FORM_ID,
  TodoForm,
  canEditTodo,
  formValuesToCreatePayload,
  formValuesToUpdatePayload,
  todoToFormValues,
  type TodoFormValues,
} from "../components/todos/TodoForm";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import {
  CheckboxField,
  SelectInput,
  TextInput,
} from "../components/ui/form";
import { FormModal } from "../components/ui/form";
import { Button } from "../components/ui/Button";
import { useModalFormCancel } from "../hooks/useModalForm";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge, type BadgeVariant } from "../components/ui/Badge";
import { FilterPanel } from "../components/ui/FilterPanel";
import { TableEntityLink } from "../components/ui/TableEntityLink";
import { TableRowActions } from "../components/ui/TableRowActions";
import { TruncatedText } from "../components/ui/TruncatedText";
import { Tabs, TabPanel, type TabItem } from "../components/ui/Tabs";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { useServerDataTable } from "../hooks/useServerDataTable";
import {
  todoCategoryFilterOptions,
  todoCategoryLabels,
  todoLabels,
  todoPriorityLabels,
  todoPriorityOptions,
  todoStatusFilterOptions,
  todoStatusLabels,
} from "../labels/todoLabels";
import {
  canPerformTodoAction,
  getGrantedTodoPermissions,
} from "../permissions/todoPermissions";
import { Banner } from "../components/ui/Banner";
import { PageShell } from "../components/ui/PageShell";
import type { Todo, TodoPriority, TodoStatus } from "../types/todo";
import type { FollowUpFilter } from "../types/followUps";
import { FollowUpsPage } from "./FollowUpsPage";

export type TodosHubView =
  | "all"
  | "today"
  | "overdue"
  | "follow_ups"
  | "action_required"
  | "data_problem";

const TODO_TABLE_VIEWS = new Set<TodosHubView>(["all", "today", "overdue"]);

const FOLLOW_UP_VIEW_FILTER: Partial<Record<TodosHubView, FollowUpFilter>> = {
  follow_ups: "hepsi",
  action_required: "action_required",
  data_problem: "data_problem",
};

const VALID_VIEWS = new Set<TodosHubView>([
  "all",
  "today",
  "overdue",
  "follow_ups",
  "action_required",
  "data_problem",
]);

function parseTodosView(search: string): TodosHubView {
  const view = new URLSearchParams(search).get("view");
  if (view && VALID_VIEWS.has(view as TodosHubView)) {
    return view as TodosHubView;
  }
  return "all";
}

function setTodosViewInUrl(view: TodosHubView) {
  const params = new URLSearchParams(window.location.search);
  if (view === "all") {
    params.delete("view");
  } else {
    params.set("view", view);
  }
  const search = params.toString();
  const next = `/todos${search ? `?${search}` : ""}`;
  if (`${window.location.pathname}${window.location.search}` !== next) {
    window.history.pushState(null, "", next);
  }
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function TodoFormModalCancel({
  onClose,
  disabled,
}: {
  onClose: () => void;
  disabled?: boolean;
}) {
  const requestClose = useModalFormCancel(onClose);
  return (
    <Button type="button" variant="secondary" onClick={requestClose} disabled={disabled}>
      {todoLabels.cancel}
    </Button>
  );
}

type ConfirmAction =
  | { type: "archive"; todo: Todo }
  | { type: "delete"; todo: Todo }
  | null;

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

function formatUserId(value: string | null | undefined): React.ReactNode {
  if (!value) return "—";
  return <TruncatedText value={value} mono maxLength={8} />;
}

function statusBadgeVariant(status: TodoStatus): BadgeVariant {
  switch (status) {
    case "done":
      return "success";
    case "in_progress":
      return "info";
    case "cancelled":
      return "neutral";
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

function canCompleteTodo(todo: Todo): boolean {
  return todo.status !== "done" && todo.status !== "archived" && todo.status !== "cancelled";
}

function canArchiveTodo(todo: Todo): boolean {
  return todo.status !== "archived";
}

interface TodosPageProps {
  onOpenDetail?: (todoId: string) => void;
  onOpenCustomer?: (customerId: string) => void;
}

export function TodosPage({ onOpenDetail, onOpenCustomer }: TodosPageProps) {
  const grantedPermissions = React.useMemo(() => getGrantedTodoPermissions(), []);
  const canRead = canPerformTodoAction(grantedPermissions, "read");
  const canCreate = canPerformTodoAction(grantedPermissions, "create");
  const canUpdate = canPerformTodoAction(grantedPermissions, "update");
  const canArchive = canPerformTodoAction(grantedPermissions, "archive");
  const canDelete = canPerformTodoAction(grantedPermissions, "delete");

  const [view, setView] = React.useState<TodosHubView>(() =>
    parseTodosView(window.location.search),
  );
  const [success, setSuccess] = React.useState<string | null>(null);
  const [modal, setModal] = React.useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = React.useState<Todo | null>(null);
  const [completingTodo, setCompletingTodo] = React.useState<Todo | null>(null);
  const [confirm, setConfirm] = React.useState<ConfirmAction>(null);
  const [actionLoadingId, setActionLoadingId] = React.useState<string | null>(null);
  const [formSaving, setFormSaving] = React.useState(false);

  React.useEffect(() => {
    if (modal === null) setFormSaving(false);
  }, [modal]);

  React.useEffect(() => {
    const onPopState = () => setView(parseTodosView(window.location.search));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const handleViewChange = (next: TodosHubView) => {
    setView(next);
    setTodosViewInUrl(next);
  };

  const isTodoTableView = TODO_TABLE_VIEWS.has(view);
  const followUpFilter = FOLLOW_UP_VIEW_FILTER[view];

  const table = useServerDataTable<Todo>({
    fetchFn: (params) =>
      listTodos({
        ...params,
        status: params.filters.status || undefined,
        priority: params.filters.priority || undefined,
        category: params.filters.category || undefined,
        assignee_user_id: params.filters.assignee_user_id || undefined,
        created_by: params.filters.created_by || undefined,
        is_overdue:
          view === "overdue"
            ? true
            : params.filters.is_overdue === "true"
              ? true
              : params.filters.is_overdue === "false"
                ? false
                : undefined,
        due_today: view === "today" ? true : undefined,
        include_archived: params.filters.include_archived === "true",
      }),
    defaultSort: { field: "updated_at", direction: "desc" },
    filterKeys: [
      "status",
      "priority",
      "category",
      "assignee_user_id",
      "created_by",
      "is_overdue",
      "include_archived",
    ],
    urlSync: isTodoTableView,
    urlPath: "/todos",
    enabled: canRead && isTodoTableView,
  });

  React.useEffect(() => {
    if (!success) return undefined;
    const timer = window.setTimeout(() => setSuccess(null), 5000);
    return () => window.clearTimeout(timer);
  }, [success]);

  React.useEffect(() => {
    if (!canRead || !isTodoTableView) return;
    void table.refresh();
  }, [view]);

  const refreshAfterAction = async () => {
    if (isTodoTableView) {
      await table.refresh();
    }
  };

  const handleCreate = async (values: TodoFormValues) => {
    await createTodo(formValuesToCreatePayload(values));
    setModal(null);
    setSuccess(todoLabels.createSuccess);
    await refreshAfterAction();
  };

  const handleUpdate = async (values: TodoFormValues) => {
    if (!editing) return;
    await updateTodo(editing.id, formValuesToUpdatePayload(values));
    setModal(null);
    setEditing(null);
    setSuccess(todoLabels.updateSuccess);
    await refreshAfterAction();
  };

  const handleCompleteSuccess = async () => {
    setCompletingTodo(null);
    setSuccess(todoLabels.completeSuccess);
    await refreshAfterAction();
  };

  const handleArchive = async (todo: Todo) => {
    setActionLoadingId(todo.id);
    try {
      await archiveTodo(todo.id);
      setConfirm(null);
      setSuccess(todoLabels.archiveSuccess);
      await refreshAfterAction();
    } catch (err) {
      console.error(err instanceof ApiError ? err.message : todoLabels.loadError);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleDelete = async (todo: Todo) => {
    setActionLoadingId(todo.id);
    try {
      await deleteTodo(todo.id);
      setConfirm(null);
      setSuccess(todoLabels.deleteSuccess);
      await refreshAfterAction();
    } catch (err) {
      console.error(err instanceof ApiError ? err.message : todoLabels.loadError);
    } finally {
      setActionLoadingId(null);
    }
  };

  const columns = React.useMemo<UniversalDataTableColumn<Todo>[]>(() => {
    const cols: UniversalDataTableColumn<Todo>[] = [
      {
        key: "title",
        title: todoLabels.colTitle,
        sortField: "title",
        render: (todo) =>
          onOpenDetail ? (
            <TableEntityLink onClick={() => onOpenDetail(todo.id)}>
              {todo.title}
            </TableEntityLink>
          ) : (
            <span className="todo-title-cell">{todo.title}</span>
          ),
      },
      {
        key: "status",
        title: todoLabels.colStatus,
        sortField: "status",
        render: (todo) => (
          <Badge variant={statusBadgeVariant(todo.status)}>
            {todoStatusLabels[todo.status]}
          </Badge>
        ),
      },
      {
        key: "priority",
        title: todoLabels.colPriority,
        sortField: "priority",
        render: (todo) => (
          <Badge variant={priorityBadgeVariant(todo.priority)}>
            {todoPriorityLabels[todo.priority]}
          </Badge>
        ),
      },
      {
        key: "category",
        title: todoLabels.colCategory,
        priority: "secondary",
        render: (todo) => todoCategoryLabels[todo.category],
      },
      {
        key: "deadline",
        title: todoLabels.colDeadline,
        sortField: "deadline",
        render: (todo) => formatDateTime(todo.deadline),
      },
      {
        key: "is_overdue",
        title: todoLabels.colOverdue,
        sortable: false,
        render: (todo) =>
          todo.is_overdue ? <Badge variant="danger">{todoLabels.overdueBadge}</Badge> : "—",
      },
      {
        key: "created_by",
        title: todoLabels.colCreatedBy,
        sortable: false,
        priority: "technical",
        render: (todo) => formatUserId(todo.created_by),
      },
      {
        key: "assignee_user_id",
        title: todoLabels.colAssignee,
        sortable: false,
        priority: "technical",
        render: (todo) => formatUserId(todo.assignee_user_id),
      },
      {
        key: "updated_at",
        title: todoLabels.colUpdatedAt,
        sortField: "updated_at",
        priority: "secondary",
        render: (todo) => formatDateTime(todo.updated_at),
      },
      {
        key: "actions",
        title: todoLabels.colActions,
        sortable: false,
        priority: "primary",
        className: "actions",
        render: (todo) => {
          const loading = actionLoadingId === todo.id;
          return (
            <TableRowActions>
              {canUpdate && canEditTodo(todo) ? (
                <button
                  type="button"
                  className="btn link"
                  disabled={loading}
                  onClick={() => {
                    setEditing(todo);
                    setModal("edit");
                  }}
                >
                  {todoLabels.actionEdit}
                </button>
              ) : null}
              {canUpdate && canCompleteTodo(todo) ? (
                <button
                  type="button"
                  className="btn link"
                  disabled={loading}
                  onClick={() => setCompletingTodo(todo)}
                >
                  {todoLabels.actionComplete}
                </button>
              ) : null}
              {canArchive && canArchiveTodo(todo) ? (
                <button
                  type="button"
                  className="btn link"
                  disabled={loading}
                  onClick={() => setConfirm({ type: "archive", todo })}
                >
                  {todoLabels.actionArchive}
                </button>
              ) : null}
              {canDelete ? (
                <button
                  type="button"
                  className="btn link danger"
                  disabled={loading}
                  onClick={() => setConfirm({ type: "delete", todo })}
                >
                  {todoLabels.actionDelete}
                </button>
              ) : null}
            </TableRowActions>
          );
        },
      },
    ];
    return cols;
  }, [actionLoadingId, canArchive, canDelete, canUpdate, onOpenDetail]);

  const tabItems = React.useMemo<TabItem<TodosHubView>[]>(
    () => [
      { id: "all", label: todoLabels.viewAll },
      { id: "today", label: todoLabels.viewToday },
      { id: "overdue", label: todoLabels.viewOverdue },
      { id: "follow_ups", label: todoLabels.viewFollowUps },
      { id: "action_required", label: todoLabels.viewActionRequired },
      { id: "data_problem", label: todoLabels.viewDataProblem },
    ],
    [],
  );

  if (!canRead) {
    return (
      <PageShell>
        <PageHeader title={todoLabels.pageTitle} subtitle={todoLabels.pageSubtitle} />
        <EmptyState title={todoLabels.permissionDenied} />
      </PageShell>
    );
  }

  const headerSubtitle = isTodoTableView
    ? `${table.pagination.totalItems} kayıt`
    : todoLabels.pageSubtitle;

  const todoTable = (
    <UniversalDataTable
      table={table}
      skeletonCols={10}
      toolbar={
        <FilterPanel
          className="todo-filters"
          actions={
            <button type="button" className="btn secondary" onClick={() => void table.refresh()}>
              Yenile
            </button>
          }
        >
          <TextInput
            id="todo-search"
            type="search"
            className="search-input"
            placeholder={todoLabels.searchPlaceholder}
            value={table.search}
            onChange={(event) => table.setSearch(event.target.value)}
            aria-label={todoLabels.searchPlaceholder}
          />
          <SelectInput
            id="todo-filter-status"
            value={table.filters.status ?? ""}
            onChange={(event) => table.setFilter("status", event.target.value)}
            aria-label={todoLabels.filterStatus}
          >
            <option value="">{todoLabels.filterAll}</option>
            {todoStatusFilterOptions.map((status) => (
              <option key={status} value={status}>
                {todoStatusLabels[status]}
              </option>
            ))}
          </SelectInput>
          <SelectInput
            id="todo-filter-priority"
            value={table.filters.priority ?? ""}
            onChange={(event) => table.setFilter("priority", event.target.value)}
            aria-label={todoLabels.filterPriority}
          >
            <option value="">{todoLabels.filterAll}</option>
            {todoPriorityOptions.map((priority) => (
              <option key={priority} value={priority}>
                {todoPriorityLabels[priority]}
              </option>
            ))}
          </SelectInput>
          <SelectInput
            id="todo-filter-category"
            value={table.filters.category ?? ""}
            onChange={(event) => table.setFilter("category", event.target.value)}
            aria-label={todoLabels.filterCategory}
          >
            <option value="">{todoLabels.filterAll}</option>
            {todoCategoryFilterOptions.map((category) => (
              <option key={category} value={category}>
                {todoCategoryLabels[category]}
              </option>
            ))}
          </SelectInput>
          {view === "all" ? (
            <SelectInput
              id="todo-filter-overdue"
              value={table.filters.is_overdue ?? ""}
              onChange={(event) => table.setFilter("is_overdue", event.target.value)}
              aria-label={todoLabels.filterOverdue}
            >
              <option value="">{todoLabels.filterAll}</option>
              <option value="true">{todoLabels.filterOverdueYes}</option>
              <option value="false">{todoLabels.filterOverdueNo}</option>
            </SelectInput>
          ) : null}
          <TextInput
            id="todo-filter-created-by"
            type="search"
            placeholder={todoLabels.filterCreatedBy}
            value={table.filters.created_by ?? ""}
            onChange={(event) => table.setFilter("created_by", event.target.value)}
            aria-label={todoLabels.filterCreatedBy}
          />
          <TextInput
            id="todo-filter-assignee"
            type="search"
            placeholder={todoLabels.filterAssignee}
            value={table.filters.assignee_user_id ?? ""}
            onChange={(event) => table.setFilter("assignee_user_id", event.target.value)}
            aria-label={todoLabels.filterAssignee}
          />
          <CheckboxField
            id="todo-filter-include-archived"
            label={todoLabels.filterIncludeArchived}
            checked={table.filters.include_archived === "true"}
            onChange={(checked) =>
              table.setFilter("include_archived", checked ? "true" : "")
            }
            className="todo-filter-checkbox"
          />
        </FilterPanel>
      }
      columns={columns}
      rowKey={(todo) => todo.id}
      emptyState={
        <EmptyState
          title={
            table.hasActiveFilters ? todoLabels.emptyFilteredTitle : todoLabels.emptyTitle
          }
          description={
            table.hasActiveFilters
              ? todoLabels.emptyFilteredDescription
              : todoLabels.emptyDescription
          }
        />
      }
    />
  );

  return (
    <PageShell className="todos-page">
      <PageHeader
        title={todoLabels.pageTitle}
        subtitle={headerSubtitle}
        actions={
          canCreate ? (
            <button
              type="button"
              className="btn primary"
              onClick={() => {
                setEditing(null);
                setModal("create");
              }}
            >
              {todoLabels.newTodo}
            </button>
          ) : undefined
        }
      />

      <Tabs
        items={tabItems}
        active={view}
        onChange={handleViewChange}
        ariaLabel={todoLabels.viewTabsAriaLabel}
      />

      <TabPanel id="panel-all" labelledBy="tab-all" active={view === "all"}>
        {todoTable}
      </TabPanel>
      <TabPanel id="panel-today" labelledBy="tab-today" active={view === "today"}>
        {todoTable}
      </TabPanel>
      <TabPanel id="panel-overdue" labelledBy="tab-overdue" active={view === "overdue"}>
        {todoTable}
      </TabPanel>
      <TabPanel
        id="panel-follow_ups"
        labelledBy="tab-follow_ups"
        active={view === "follow_ups"}
      >
        {view === "follow_ups" && followUpFilter ? (
          <FollowUpsPage
            key="follow_ups"
            embedded
            hidePageChrome
            lockedFilter={followUpFilter}
            urlPath="/todos"
            onOpenCustomer={onOpenCustomer}
          />
        ) : null}
      </TabPanel>
      <TabPanel
        id="panel-action_required"
        labelledBy="tab-action_required"
        active={view === "action_required"}
      >
        {view === "action_required" && followUpFilter ? (
          <FollowUpsPage
            key="action_required"
            embedded
            hidePageChrome
            lockedFilter={followUpFilter}
            urlPath="/todos"
            onOpenCustomer={onOpenCustomer}
          />
        ) : null}
      </TabPanel>
      <TabPanel
        id="panel-data_problem"
        labelledBy="tab-data_problem"
        active={view === "data_problem"}
      >
        {view === "data_problem" && followUpFilter ? (
          <FollowUpsPage
            key="data_problem"
            embedded
            hidePageChrome
            lockedFilter={followUpFilter}
            urlPath="/todos"
            onOpenCustomer={onOpenCustomer}
          />
        ) : null}
      </TabPanel>

      {success ? <Banner variant="success">{success}</Banner> : null}

      {modal === "create" ? (
        <FormModal
          title={todoLabels.newTodo}
          onClose={() => setModal(null)}
          size="lg"
          formWidth="standard"
          footer={
            <>
              <TodoFormModalCancel onClose={() => setModal(null)} disabled={formSaving} />
              <Button
                type="submit"
                form={TODO_FORM_ID}
                variant="primary"
                loading={formSaving}
              >
                {formSaving ? todoLabels.saving : todoLabels.save}
              </Button>
            </>
          }
        >
          <TodoForm onSubmit={handleCreate} onSavingChange={setFormSaving} />
        </FormModal>
      ) : null}

      {modal === "edit" && editing ? (
        <FormModal
          title={todoLabels.editTodo}
          onClose={() => setModal(null)}
          size="lg"
          formWidth="standard"
          footer={
            <>
              <TodoFormModalCancel onClose={() => setModal(null)} disabled={formSaving} />
              <Button
                type="submit"
                form={TODO_FORM_ID}
                variant="primary"
                loading={formSaving}
              >
                {formSaving ? todoLabels.saving : todoLabels.save}
              </Button>
            </>
          }
        >
          <TodoForm
            initial={todoToFormValues(editing)}
            onSubmit={handleUpdate}
            onSavingChange={setFormSaving}
          />
        </FormModal>
      ) : null}

      {completingTodo ? (
        <CompleteTodoModal
          todo={completingTodo}
          onClose={() => setCompletingTodo(null)}
          onCompleted={() => void handleCompleteSuccess()}
        />
      ) : null}

      {confirm?.type === "archive" ? (
        <ConfirmDialog
          title={todoLabels.archiveConfirmTitle}
          message={todoLabels.archiveConfirmMessage}
          confirmLabel={todoLabels.actionArchive}
          variant="danger"
          loading={actionLoadingId === confirm.todo.id}
          onCancel={() => setConfirm(null)}
          onConfirm={() => void handleArchive(confirm.todo)}
        />
      ) : null}

      {confirm?.type === "delete" ? (
        <ConfirmDialog
          title={todoLabels.deleteConfirmTitle}
          message={todoLabels.deleteConfirmMessage}
          confirmLabel={todoLabels.actionDelete}
          variant="danger"
          loading={actionLoadingId === confirm.todo.id}
          onCancel={() => setConfirm(null)}
          onConfirm={() => void handleDelete(confirm.todo)}
        />
      ) : null}
    </PageShell>
  );
}

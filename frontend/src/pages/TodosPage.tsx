import React from "react";
import {
  archiveTodo,
  completeTodo,
  createTodo,
  deleteTodo,
  listTodos,
  updateTodo,
} from "../api/todos";
import { listFairs } from "../api/fairs";
import { ApiError } from "../api/client";
import { isoToLocalDatetime, localDatetimeToIso } from "../components/ActivityForm";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import {
  FormActions,
  FormField,
  FormGrid,
  SelectInput,
  TextareaInput,
  TextInput,
} from "../components/ui/form";
import { FormModal } from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge, type BadgeVariant } from "../components/ui/Badge";
import { FilterPanel } from "../components/ui/FilterPanel";
import { TruncatedText } from "../components/ui/TruncatedText";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { useServerDataTable } from "../hooks/useServerDataTable";
import {
  todoCategoryLabels,
  todoCategoryOptions,
  todoFormStatusLabels,
  todoFormStatusOptions,
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
import type { Fair } from "../types/fair";
import type {
  CreateTodoPayload,
  Todo,
  TodoCategory,
  TodoFormStatus,
  TodoPriority,
  TodoStatus,
} from "../types/todo";

type ConfirmAction =
  | { type: "archive"; todo: Todo }
  | { type: "delete"; todo: Todo }
  | null;

interface TodoFormValues {
  title: string;
  description: string;
  status: TodoFormStatus;
  priority: TodoPriority;
  category: TodoCategory;
  deadline: string;
  assignee_user_id: string;
  source_fair_id: string;
}

const defaultFormValues = (): TodoFormValues => ({
  title: "",
  description: "",
  status: "todo",
  priority: "normal",
  category: "genel_gorev",
  deadline: "",
  assignee_user_id: "",
  source_fair_id: "",
});

function todoToFormValues(todo: Todo): TodoFormValues {
  const status: TodoFormStatus =
    todo.status === "todo" || todo.status === "in_progress" || todo.status === "cancelled"
      ? todo.status
      : "todo";
  return {
    title: todo.title,
    description: todo.description ?? "",
    status,
    priority: todo.priority,
    category: todo.category,
    deadline: isoToLocalDatetime(todo.deadline),
    assignee_user_id: todo.assignee_user_id ?? "",
    source_fair_id: todo.source_fair_id ?? "",
  };
}

function formValuesToCreatePayload(values: TodoFormValues): CreateTodoPayload {
  return {
    title: values.title.trim(),
    description: values.description.trim() || null,
    status: values.status,
    priority: values.priority,
    category: values.category,
    deadline: values.deadline ? localDatetimeToIso(values.deadline) : null,
    assignee_user_id: values.assignee_user_id.trim() || null,
    source_fair_id: values.source_fair_id.trim() || null,
  };
}

function formValuesToUpdatePayload(values: TodoFormValues) {
  return {
    title: values.title.trim(),
    description: values.description.trim() || null,
    status: values.status,
    priority: values.priority,
    category: values.category,
    deadline: values.deadline ? localDatetimeToIso(values.deadline) : null,
    assignee_user_id: values.assignee_user_id.trim() || null,
    source_fair_id: values.source_fair_id.trim() || null,
  };
}

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

function canEditTodo(todo: Todo): boolean {
  return todo.status !== "done" && todo.status !== "archived";
}

function canCompleteTodo(todo: Todo): boolean {
  return todo.status !== "done" && todo.status !== "archived" && todo.status !== "cancelled";
}

function canArchiveTodo(todo: Todo): boolean {
  return todo.status !== "archived";
}

interface TodoFormProps {
  initial?: TodoFormValues;
  fairs: Fair[];
  submitLabel: string;
  onCancel: () => void;
  onSubmit: (values: TodoFormValues) => Promise<void>;
}

function TodoForm({ initial, fairs, submitLabel, onCancel, onSubmit }: TodoFormProps) {
  const [values, setValues] = React.useState<TodoFormValues>(initial ?? defaultFormValues());
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setValues(initial ?? defaultFormValues());
    setError(null);
  }, [initial]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!values.title.trim()) {
      setError(todoLabels.titleRequired);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSubmit(values);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : todoLabels.loadError);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={(event) => void handleSubmit(event)}>
      <FormGrid>
        <FormField label={todoLabels.fieldTitle} htmlFor="todo-title" required fullWidth>
          <TextInput
            id="todo-title"
            value={values.title}
            onChange={(event) => setValues((prev) => ({ ...prev, title: event.target.value }))}
            required
          />
        </FormField>
        <FormField label={todoLabels.fieldDescription} htmlFor="todo-description" fullWidth>
          <TextareaInput
            id="todo-description"
            value={values.description}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, description: event.target.value }))
            }
            rows={4}
          />
        </FormField>
        <FormField label={todoLabels.fieldStatus} htmlFor="todo-status">
          <SelectInput
            id="todo-status"
            value={values.status}
            onChange={(event) =>
              setValues((prev) => ({
                ...prev,
                status: event.target.value as TodoFormStatus,
              }))
            }
          >
            {todoFormStatusOptions.map((status) => (
              <option key={status} value={status}>
                {todoFormStatusLabels[status]}
              </option>
            ))}
          </SelectInput>
        </FormField>
        <FormField label={todoLabels.fieldPriority} htmlFor="todo-priority">
          <SelectInput
            id="todo-priority"
            value={values.priority}
            onChange={(event) =>
              setValues((prev) => ({
                ...prev,
                priority: event.target.value as TodoPriority,
              }))
            }
          >
            {todoPriorityOptions.map((priority) => (
              <option key={priority} value={priority}>
                {todoPriorityLabels[priority]}
              </option>
            ))}
          </SelectInput>
        </FormField>
        <FormField label={todoLabels.fieldCategory} htmlFor="todo-category">
          <SelectInput
            id="todo-category"
            value={values.category}
            onChange={(event) =>
              setValues((prev) => ({
                ...prev,
                category: event.target.value as TodoCategory,
              }))
            }
          >
            {todoCategoryOptions.map((category) => (
              <option key={category} value={category}>
                {todoCategoryLabels[category]}
              </option>
            ))}
          </SelectInput>
        </FormField>
        <FormField label={todoLabels.fieldDeadline} htmlFor="todo-deadline">
          <TextInput
            id="todo-deadline"
            type="datetime-local"
            value={values.deadline}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, deadline: event.target.value }))
            }
          />
        </FormField>
        <FormField
          label={todoLabels.fieldSourceFair}
          htmlFor="todo-source-fair"
          fullWidth
          hint={todoLabels.fieldSourceFairHint}
        >
          <SelectInput
            id="todo-source-fair"
            value={values.source_fair_id}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, source_fair_id: event.target.value }))
            }
          >
            <option value="">{todoLabels.fieldSourceFairPlaceholder}</option>
            {fairs.map((fair) => (
              <option key={fair.id} value={fair.id}>
                {fair.name}
              </option>
            ))}
          </SelectInput>
        </FormField>
        <FormField label={todoLabels.fieldAssignee} htmlFor="todo-assignee" fullWidth>
          <TextInput
            id="todo-assignee"
            value={values.assignee_user_id}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, assignee_user_id: event.target.value }))
            }
            placeholder="00000000-0000-0000-0000-000000000000"
          />
        </FormField>
        {error ? (
          <p className="field-error span-2" role="alert">
            {error}
          </p>
        ) : null}
        <FormActions
          onCancel={onCancel}
          submitLabel={submitLabel}
          cancelLabel={todoLabels.cancel}
          saving={saving}
          savingLabel={todoLabels.saving}
        />
      </FormGrid>
    </form>
  );
}

interface TodosPageProps {
  onOpenDetail?: (todoId: string) => void;
}

export function TodosPage({ onOpenDetail }: TodosPageProps) {
  const grantedPermissions = React.useMemo(() => getGrantedTodoPermissions(), []);
  const canRead = canPerformTodoAction(grantedPermissions, "read");
  const canCreate = canPerformTodoAction(grantedPermissions, "create");
  const canUpdate = canPerformTodoAction(grantedPermissions, "update");
  const canArchive = canPerformTodoAction(grantedPermissions, "archive");
  const canDelete = canPerformTodoAction(grantedPermissions, "delete");

  const [success, setSuccess] = React.useState<string | null>(null);
  const [modal, setModal] = React.useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = React.useState<Todo | null>(null);
  const [confirm, setConfirm] = React.useState<ConfirmAction>(null);
  const [actionLoadingId, setActionLoadingId] = React.useState<string | null>(null);
  const [fairs, setFairs] = React.useState<Fair[]>([]);

  React.useEffect(() => {
    listFairs({ pageSize: 100, sortBy: "name", sortOrder: "asc" })
      .then((result) => setFairs(result.items))
      .catch(() => setFairs([]));
  }, []);

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
          params.filters.is_overdue === "true"
            ? true
            : params.filters.is_overdue === "false"
              ? false
              : undefined,
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
    urlSync: true,
    urlPath: "/todos",
    enabled: canRead,
  });

  React.useEffect(() => {
    if (!success) return undefined;
    const timer = window.setTimeout(() => setSuccess(null), 5000);
    return () => window.clearTimeout(timer);
  }, [success]);

  const refreshAfterAction = async () => {
    await table.refresh();
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

  const handleComplete = async (todo: Todo) => {
    setActionLoadingId(todo.id);
    try {
      await completeTodo(todo.id);
      setSuccess(todoLabels.completeSuccess);
      await refreshAfterAction();
    } catch (err) {
      console.error(err instanceof ApiError ? err.message : todoLabels.loadError);
    } finally {
      setActionLoadingId(null);
    }
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
            <button type="button" className="link-button" onClick={() => onOpenDetail(todo.id)}>
              {todo.title}
            </button>
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
            <div className="table-actions">
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
                  onClick={() => void handleComplete(todo)}
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
            </div>
          );
        },
      },
    ];
    return cols;
  }, [actionLoadingId, canArchive, canDelete, canUpdate, onOpenDetail]);

  if (!canRead) {
    return (
      <div className="page">
        <PageHeader title={todoLabels.pageTitle} subtitle={todoLabels.pageSubtitle} />
        <EmptyState title={todoLabels.permissionDenied} />
      </div>
    );
  }

  return (
    <div className="page todos-page">
      <PageHeader
        title={todoLabels.pageTitle}
        subtitle={`${table.pagination.totalItems} kayıt`}
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
            <input
              type="search"
              className="search-input"
              placeholder={todoLabels.searchPlaceholder}
              value={table.search}
              onChange={(event) => table.setSearch(event.target.value)}
              aria-label={todoLabels.searchPlaceholder}
            />
            <select
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
            </select>
            <select
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
            </select>
            <select
              value={table.filters.category ?? ""}
              onChange={(event) => table.setFilter("category", event.target.value)}
              aria-label={todoLabels.filterCategory}
            >
              <option value="">{todoLabels.filterAll}</option>
              {todoCategoryOptions.map((category) => (
                <option key={category} value={category}>
                  {todoCategoryLabels[category]}
                </option>
              ))}
            </select>
            <select
              value={table.filters.is_overdue ?? ""}
              onChange={(event) => table.setFilter("is_overdue", event.target.value)}
              aria-label={todoLabels.filterOverdue}
            >
              <option value="">{todoLabels.filterAll}</option>
              <option value="true">{todoLabels.filterOverdueYes}</option>
              <option value="false">{todoLabels.filterOverdueNo}</option>
            </select>
            <input
              type="search"
              className="input"
              placeholder={todoLabels.filterCreatedBy}
              value={table.filters.created_by ?? ""}
              onChange={(event) => table.setFilter("created_by", event.target.value)}
              aria-label={todoLabels.filterCreatedBy}
            />
            <input
              type="search"
              className="input"
              placeholder={todoLabels.filterAssignee}
              value={table.filters.assignee_user_id ?? ""}
              onChange={(event) => table.setFilter("assignee_user_id", event.target.value)}
              aria-label={todoLabels.filterAssignee}
            />
            <label className="todo-filter-checkbox checkbox-field">
              <input
                type="checkbox"
                checked={table.filters.include_archived === "true"}
                onChange={(event) =>
                  table.setFilter("include_archived", event.target.checked ? "true" : "")
                }
              />
              <span className="checkbox-field-label">{todoLabels.filterIncludeArchived}</span>
            </label>
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

      {success ? <div className="banner success">{success}</div> : null}

      {modal === "create" ? (
        <FormModal title={todoLabels.newTodo} onClose={() => setModal(null)} size="lg">
          <TodoForm
            fairs={fairs}
            submitLabel={todoLabels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleCreate}
          />
        </FormModal>
      ) : null}

      {modal === "edit" && editing ? (
        <FormModal title={todoLabels.editTodo} onClose={() => setModal(null)} size="lg">
          <TodoForm
            fairs={fairs}
            initial={todoToFormValues(editing)}
            submitLabel={todoLabels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleUpdate}
          />
        </FormModal>
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
    </div>
  );
}

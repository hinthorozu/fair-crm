import { normalizeStandardListResponse, buildListQueryParams } from "./listTable";
import { apiRequest } from "./client";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import type {
  CompleteTodoPayload,
  CreateTodoPayload,
  Todo,
  UpdateTodoPayload,
} from "../types/todo";

export interface ListTodosParams extends Partial<ServerTableFetchParams> {
  status?: string;
  priority?: string;
  category?: string;
  assignee_user_id?: string;
  created_by?: string;
  is_overdue?: boolean;
  due_today?: boolean;
  include_archived?: boolean;
}

export async function listTodos(params: ListTodosParams = {}): Promise<StandardListResponse<Todo>> {
  const filters: Record<string, string | undefined> = { ...params.filters };

  const status = params.status ?? filters.status;
  const priority = params.priority ?? filters.priority;
  const category = params.category ?? filters.category;
  const assignee = params.assignee_user_id ?? filters.assignee_user_id;
  const createdBy = params.created_by ?? filters.created_by;

  if (status) filters.status = status;
  if (priority) filters.priority = priority;
  if (category) filters.category = category;
  if (assignee) filters.assignee_user_id = assignee;
  if (createdBy) filters.created_by = createdBy;

  if (params.is_overdue === true) {
    filters.is_overdue = "true";
  } else if (params.is_overdue === false) {
    filters.is_overdue = "false";
  }

  if (params.due_today === true) {
    filters.due_today = "true";
  } else if (params.due_today === false) {
    filters.due_today = "false";
  }

  if (params.include_archived) {
    filters.include_archived = "true";
  }

  const query = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters,
  });
  const raw = await apiRequest<unknown>(`/api/v1/todos?${query.toString()}`);
  return normalizeStandardListResponse<Todo>(raw);
}

export function getTodo(id: string): Promise<Todo> {
  return apiRequest<Todo>(`/api/v1/todos/${id}`);
}

export function createTodo(payload: CreateTodoPayload): Promise<Todo> {
  return apiRequest<Todo>("/api/v1/todos", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateTodo(id: string, payload: UpdateTodoPayload): Promise<Todo> {
  return apiRequest<Todo>(`/api/v1/todos/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function completeTodo(
  id: string,
  payload: CompleteTodoPayload = {},
): Promise<Todo> {
  return apiRequest<Todo>(`/api/v1/todos/${id}/complete`, {
    method: "POST",
    body: JSON.stringify({
      note: payload.note?.trim() ? payload.note.trim() : null,
    }),
  });
}

export function archiveTodo(id: string): Promise<Todo> {
  return apiRequest<Todo>(`/api/v1/todos/${id}/archive`, {
    method: "POST",
  });
}

export function deleteTodo(id: string): Promise<void> {
  return apiRequest<void>(`/api/v1/todos/${id}`, {
    method: "DELETE",
  });
}

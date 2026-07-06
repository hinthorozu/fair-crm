import { buildListQueryParams, normalizeStandardListResponse } from "./listTable";
import { apiRequest } from "./client";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import type {
  RecordTodoWorklistActivityPayload,
  RecordTodoWorklistActivityResult,
  TodoWorklistModalContext,
  TodoWorklistProgress,
  TodoWorklistRow,
  WorklistFilter,
} from "../types/todoWorklist";

export interface ListTodoWorklistParams extends Partial<ServerTableFetchParams> {
  filter?: WorklistFilter;
}

export async function listTodoWorklist(
  todoId: string,
  params: ListTodoWorklistParams = {},
): Promise<StandardListResponse<TodoWorklistRow>> {
  const filters: Record<string, string | undefined> = { ...params.filters };
  const filter = params.filter ?? filters.filter ?? "yapilmadi";
  filters.filter = filter;

  const query = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters,
  });
  const raw = await apiRequest<unknown>(`/api/v1/todos/${todoId}/worklist?${query.toString()}`);
  return normalizeStandardListResponse<TodoWorklistRow>(raw);
}

export function getTodoWorklistProgress(todoId: string): Promise<TodoWorklistProgress> {
  return apiRequest<TodoWorklistProgress>(`/api/v1/todos/${todoId}/worklist/progress`);
}

export function getTodoWorklistModalContext(
  todoId: string,
  customerId: string,
): Promise<TodoWorklistModalContext> {
  return apiRequest<TodoWorklistModalContext>(
    `/api/v1/todos/${todoId}/worklist/customers/${customerId}/modal`,
  );
}

export function recordTodoWorklistActivity(
  todoId: string,
  customerId: string,
  payload: RecordTodoWorklistActivityPayload,
): Promise<RecordTodoWorklistActivityResult> {
  return apiRequest<RecordTodoWorklistActivityResult>(
    `/api/v1/todos/${todoId}/worklist/customers/${customerId}/activities`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

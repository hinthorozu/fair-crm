import { normalizeStandardListResponse, buildListQueryParams } from "./listTable";
import { apiRequest } from "./client";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import {
  isManualActivityType,
  type Activity,
  type ActivityType,
  type BulkDeleteActivitiesResult,
  type CreateActivityPayload,
  type UpdateActivityPayload,
} from "../types/activity";

export interface ListActivitiesParams extends Partial<ServerTableFetchParams> {
  activityType?: ActivityType;
  customerId?: string;
  status?: string;
  dateFrom?: string;
  dateTo?: string;
}

type CreateActivityInput = Omit<CreateActivityPayload, "type"> & { type: ActivityType };

export async function listActivities(
  params: ListActivitiesParams = {},
): Promise<StandardListResponse<Activity>> {
  const query = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters: {
      ...(params.activityType ? { activityType: params.activityType } : {}),
      ...(params.customerId ? { customerId: params.customerId } : {}),
      ...(params.status ? { status: params.status } : {}),
      ...(params.dateFrom ? { dateFrom: params.dateFrom } : {}),
      ...(params.dateTo ? { dateTo: params.dateTo } : {}),
      ...params.filters,
    },
  });
  const raw = await apiRequest<unknown>(`/api/v1/activities?${query.toString()}`);
  return normalizeStandardListResponse<Activity>(raw);
}

export async function listActivitiesByCustomer(
  customerId: string,
  params: ListActivitiesParams = {},
): Promise<StandardListResponse<Activity>> {
  const query = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters: {
      ...(params.activityType ? { activityType: params.activityType } : {}),
      ...params.filters,
    },
  });
  const raw = await apiRequest<unknown>(
    `/api/v1/customers/${encodeURIComponent(customerId)}/activities?${query.toString()}`,
  );
  return normalizeStandardListResponse<Activity>(raw);
}

export function getActivity(id: string): Promise<Activity> {
  return apiRequest<Activity>(`/api/v1/activities/${encodeURIComponent(id)}`);
}

export async function createActivity(input: CreateActivityInput): Promise<Activity> {
  if (!isManualActivityType(input.type)) {
    throw new Error("task_completed is system-only and cannot be created manually.");
  }
  const payload: CreateActivityPayload = { ...input, type: input.type };
  return apiRequest<Activity>("/api/v1/activities", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateActivity(id: string, payload: UpdateActivityPayload): Promise<Activity> {
  return apiRequest<Activity>(`/api/v1/activities/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteActivity(id: string): Promise<void> {
  return apiRequest<void>(`/api/v1/activities/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export function bulkDeleteActivities(activityIds: string[]): Promise<BulkDeleteActivitiesResult> {
  return apiRequest<BulkDeleteActivitiesResult>("/api/v1/activities/bulk-delete", {
    method: "POST",
    body: JSON.stringify({ activity_ids: activityIds }),
  });
}

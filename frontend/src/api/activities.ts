import { normalizeStandardListResponse, buildListQueryParams } from "./listTable";
import { apiRequest } from "./client";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import type {
  Activity,
  ActivityType,
  CreateActivityPayload,
  UpdateActivityPayload,
} from "../types/activity";

export interface ListActivitiesParams extends Partial<ServerTableFetchParams> {
  activityType?: ActivityType;
}

export async function listActivitiesByCustomer(
  customerId: string,
  params: ListActivitiesParams = {},
): Promise<StandardListResponse<Activity>> {
  const query = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sort: params.sort,
    direction: params.direction,
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

export function createActivity(payload: CreateActivityPayload): Promise<Activity> {
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

export function deleteActivity(id: string): Promise<Activity> {
  return apiRequest<Activity>(`/api/v1/activities/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

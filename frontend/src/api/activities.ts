import { normalizePaginatedResponse } from "./pagination";
import { apiRequest } from "./client";
import type {
  Activity,
  ActivityListResponse,
  CreateActivityPayload,
  ListActivitiesParams,
  UpdateActivityPayload,
} from "../types/activity";
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE } from "../types/pagination";

function buildQuery(params: ListActivitiesParams): string {
  const q = new URLSearchParams();
  q.set("page", String(params.page ?? DEFAULT_PAGE));
  q.set("page_size", String(params.page_size ?? DEFAULT_PAGE_SIZE));
  if (params.sort_by) q.set("sort_by", params.sort_by);
  if (params.sort_dir) q.set("sort_dir", params.sort_dir);
  return `?${q.toString()}`;
}

export async function listActivitiesByCustomer(
  customerId: string,
  params: ListActivitiesParams = {},
): Promise<ActivityListResponse> {
  const page = params.page ?? DEFAULT_PAGE;
  const page_size = params.page_size ?? DEFAULT_PAGE_SIZE;
  const raw = await apiRequest<unknown>(
    `/api/v1/customers/${encodeURIComponent(customerId)}/activities${buildQuery(params)}`,
  );
  return normalizePaginatedResponse<Activity>(raw, { page, page_size });
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

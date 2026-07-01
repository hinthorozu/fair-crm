import { normalizePaginatedResponse } from "./pagination";
import { apiRequest, ApiError, formatApiErrorMessage } from "./client";
import type {
  CreateFairPayload,
  Fair,
  FairListResponse,
  ListFairsParams,
  UpdateFairPayload,
} from "../types/fair";
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE } from "../types/pagination";

function buildQuery(params: ListFairsParams): string {
  const q = new URLSearchParams();
  if (params.search) q.set("search", params.search);
  if (params.status) q.set("status", params.status);
  q.set("page", String(params.page ?? DEFAULT_PAGE));
  q.set("page_size", String(params.page_size ?? DEFAULT_PAGE_SIZE));
  if (params.sort_by) q.set("sort_by", params.sort_by);
  if (params.sort_dir) q.set("sort_dir", params.sort_dir);
  return `?${q.toString()}`;
}

export async function listFairs(params: ListFairsParams = {}): Promise<FairListResponse> {
  const page = params.page ?? DEFAULT_PAGE;
  const page_size = params.page_size ?? DEFAULT_PAGE_SIZE;
  const raw = await apiRequest<unknown>(`/api/v1/fairs${buildQuery(params)}`);
  return normalizePaginatedResponse<Fair>(raw, { page, page_size });
}

export function getFair(id: string): Promise<Fair> {
  return apiRequest<Fair>(`/api/v1/fairs/${id}`);
}

export function createFair(payload: CreateFairPayload): Promise<Fair> {
  return apiRequest<Fair>("/api/v1/fairs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateFair(id: string, payload: UpdateFairPayload): Promise<Fair> {
  return apiRequest<Fair>(`/api/v1/fairs/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function archiveFair(id: string): Promise<Fair> {
  return apiRequest<Fair>(`/api/v1/fairs/${id}`, {
    method: "DELETE",
  });
}

export function restoreFair(id: string): Promise<Fair> {
  const fairId = id?.trim();
  if (!fairId) {
    return Promise.reject(new ApiError("Fuar kimliği eksik.", 400));
  }
  return apiRequest<Fair>(`/api/v1/fairs/${encodeURIComponent(fairId)}/restore`, {
    method: "POST",
  });
}

export { ApiError, formatApiErrorMessage };

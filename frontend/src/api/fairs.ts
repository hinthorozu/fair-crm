import { normalizeStandardListResponse, buildListQueryParams } from "./listTable";
import { apiRequest, ApiError, formatApiErrorMessage } from "./client";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import type { CreateFairPayload, Fair, UpdateFairPayload, FairStatus } from "../types/fair";
import type { ScraperRun } from "../types/scraper";

export interface ListFairsParams extends Partial<ServerTableFetchParams> {
  status?: FairStatus;
  country?: string;
}

export async function listFairs(params: ListFairsParams = {}): Promise<StandardListResponse<Fair>> {
  const query = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters: {
      ...(params.status ? { status: params.status } : {}),
      ...(params.country ? { country: params.country } : {}),
      ...params.filters,
    },
  });
  const raw = await apiRequest<unknown>(`/api/v1/fairs?${query.toString()}`);
  return normalizeStandardListResponse<Fair>(raw);
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

export function runFairScraper(fairId: string): Promise<ScraperRun> {
  return apiRequest<ScraperRun>(`/api/v1/fairs/${encodeURIComponent(fairId)}/run`, {
    method: "POST",
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

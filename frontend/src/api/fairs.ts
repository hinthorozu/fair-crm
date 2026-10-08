import { normalizeStandardListResponse, buildListQueryParams } from "./listTable";
import { apiRequest, ApiError, formatApiErrorMessage } from "./client";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import type { CreateFairPayload, Fair, UpdateFairPayload, FairStatus } from "../types/fair";
import type { EnrichmentRunPayload, ScraperRun } from "../types/scraper";
import { FAIR_READ } from "../permissions/fairPermissions";
import { getGrantedCorePermissions } from "../permissions/corePermissions";

const FAIR_READ_DENIED = `Fuar bilgilerini görüntüleme yetkiniz yok (${FAIR_READ}).`;

export interface ListFairsParams extends Partial<ServerTableFetchParams> {
  status?: FairStatus;
  country?: string;
}

export async function listFairs(params: ListFairsParams = {}): Promise<StandardListResponse<Fair>> {
  if (!getGrantedCorePermissions().has(FAIR_READ)) {
    throw new ApiError(FAIR_READ_DENIED, 403);
  }
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
  // FastAPI AliasChoices on `direction` does not bind `sort_order`; `sort_dir` is accepted.
  const sortOrder = query.get("sort_order");
  if (sortOrder) query.set("sort_dir", sortOrder);
  const raw = await apiRequest<unknown>(`/api/v1/fairs?${query.toString()}`);
  return normalizeStandardListResponse<Fair>(raw);
}

export function getFair(id: string): Promise<Fair> {
  if (!getGrantedCorePermissions().has(FAIR_READ)) {
    return Promise.reject(new ApiError(FAIR_READ_DENIED, 403));
  }
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

export interface TobbSyncConflictItem {
  name: string;
  identity_name: string;
  city: string | null;
  fair_ids: string[];
}

export interface SyncTobbSystemFairsResponse {
  inserted: number;
  updated: number;
  conflicts: number;
  conflict_items?: TobbSyncConflictItem[];
}

export interface SystemFairDuplicateFair {
  id: string;
  name: string;
  city: string | null;
  start_date: string | null;
  end_date: string | null;
  organizer: string | null;
  website: string | null;
  external_id: string | null;
  source: string | null;
  participations: number;
  todos: number;
  quotes: number;
  imports: number;
  scraper_runs: number;
  has_scraper_config: boolean;
}

export interface SystemFairDuplicateGroup {
  identity_name: string;
  city: string | null;
  fairs: SystemFairDuplicateFair[];
}

export interface SystemFairMergePreview {
  participations: number;
  todos: number;
  quotes: number;
  activities: number;
  imports: number;
  scraper_runs: number;
  email_batches: number;
  mail_operations: number;
  operations: number;
  blocking_conflicts: { code: string; message: string }[];
}

export function listSystemFairDuplicates(): Promise<{ items: SystemFairDuplicateGroup[] }> {
  return apiRequest<{ items: SystemFairDuplicateGroup[] }>("/api/v1/fairs/system/duplicates");
}

export function previewSystemFairMerge(
  sourceFairId: string,
  targetFairId: string,
): Promise<SystemFairMergePreview> {
  return apiRequest<SystemFairMergePreview>("/api/v1/fairs/system/duplicates/preview", {
    method: "POST",
    body: JSON.stringify({ source_fair_id: sourceFairId, target_fair_id: targetFairId }),
  });
}

export function mergeSystemFair(
  sourceFairId: string,
  targetFairId: string,
): Promise<SystemFairMergePreview> {
  return apiRequest<SystemFairMergePreview>(
    `/api/v1/fairs/system/${encodeURIComponent(sourceFairId)}/merge`,
    {
      method: "POST",
      body: JSON.stringify({ target_fair_id: targetFairId }),
    },
  );
}

export function keepSystemFairsSeparate(fairIds: string[]): Promise<{ separated: number }> {
  return apiRequest<{ separated: number }>("/api/v1/fairs/system/duplicates/keep-separate", {
    method: "POST",
    body: JSON.stringify({ fair_ids: fairIds }),
  });
}

export function syncTobbSystemFairs(year: number): Promise<SyncTobbSystemFairsResponse> {
  return apiRequest<SyncTobbSystemFairsResponse>("/api/v1/fairs/system/tobb/sync", {
    method: "POST",
    body: JSON.stringify({ year }),
  });
}

export interface CompareSystemFairImportResponse {
  batch_id: string;
}

export function compareSystemFairImport(fairId: string): Promise<CompareSystemFairImportResponse> {
  return apiRequest<CompareSystemFairImportResponse>(
    `/api/v1/fairs/${encodeURIComponent(fairId)}/compare-import`,
    { method: "POST" },
  );
}

export function runFairContactEnrichment(
  fairId: string,
  body: EnrichmentRunPayload = {},
): Promise<ScraperRun> {
  return apiRequest<ScraperRun>(
    `/api/v1/fairs/${encodeURIComponent(fairId)}/contact-enrichment/run`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
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

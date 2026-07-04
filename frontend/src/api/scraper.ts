import { apiRequest } from "./client";
import type {
  ScraperDashboardResponse,
  ScraperManifest,
  ScraperManifestListResponse,
  ScraperRun,
  ScraperRunListResponse,
  ScraperRunLogListResponse,
  AdapterLinkedFairListResponse,
  AdapterListResponse,
  AdapterDetail,
  CreateAdapterPayload,
  UpdateAdapterPayload,
} from "../types/scraper";

export async function getScraperDashboard(): Promise<ScraperDashboardResponse> {
  return apiRequest<ScraperDashboardResponse>("/api/v1/scraper/dashboard");
}

export async function getScraperManifests(): Promise<ScraperManifestListResponse> {
  return apiRequest<ScraperManifestListResponse>("/api/v1/scraper/manifests");
}

export async function listAdapters(): Promise<AdapterListResponse> {
  return apiRequest<AdapterListResponse>("/api/v1/scraper/adapters");
}

export async function getAdapter(adapterKey: string): Promise<AdapterDetail> {
  return apiRequest<AdapterDetail>(`/api/v1/scraper/adapters/${encodeURIComponent(adapterKey)}`);
}

export async function createAdapter(payload: CreateAdapterPayload): Promise<AdapterDetail> {
  return apiRequest<AdapterDetail>("/api/v1/scraper/adapters", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateAdapter(adapterKey: string, payload: UpdateAdapterPayload): Promise<AdapterDetail> {
  return apiRequest<AdapterDetail>(`/api/v1/scraper/adapters/${encodeURIComponent(adapterKey)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function activateAdapter(adapterKey: string): Promise<AdapterDetail> {
  return apiRequest<AdapterDetail>(`/api/v1/scraper/adapters/${encodeURIComponent(adapterKey)}/activate`, {
    method: "POST",
  });
}

export async function deactivateAdapter(adapterKey: string): Promise<AdapterDetail> {
  return apiRequest<AdapterDetail>(`/api/v1/scraper/adapters/${encodeURIComponent(adapterKey)}/deactivate`, {
    method: "POST",
  });
}

export async function getScraperManifest(adapterKey: string): Promise<ScraperManifest> {
  return apiRequest<ScraperManifest>(`/api/v1/scraper/manifests/${encodeURIComponent(adapterKey)}`);
}

export async function listScraperRuns(params?: {
  limit?: number;
  offset?: number;
  fair_id?: string;
}): Promise<ScraperRunListResponse> {
  const search = new URLSearchParams();
  if (params?.limit != null) search.set("limit", String(params.limit));
  if (params?.offset != null) search.set("offset", String(params.offset));
  if (params?.fair_id) search.set("fair_id", params.fair_id);
  const qs = search.toString();
  return apiRequest<ScraperRunListResponse>(`/api/v1/scraper/runs${qs ? `?${qs}` : ""}`);
}

export async function getScraperRun(runId: string): Promise<ScraperRun> {
  return apiRequest<ScraperRun>(`/api/v1/scraper/runs/${encodeURIComponent(runId)}`);
}

export async function listScraperRunLogs(
  runId: string,
  params?: { after_id?: string; limit?: number },
): Promise<ScraperRunLogListResponse> {
  const search = new URLSearchParams();
  if (params?.after_id) search.set("after_id", params.after_id);
  if (params?.limit != null) search.set("limit", String(params.limit));
  const qs = search.toString();
  return apiRequest<ScraperRunLogListResponse>(
    `/api/v1/scraper/runs/${encodeURIComponent(runId)}/logs${qs ? `?${qs}` : ""}`,
  );
}

export async function getAdapterLinkedFairs(adapterKey: string): Promise<AdapterLinkedFairListResponse> {
  return apiRequest<AdapterLinkedFairListResponse>(
    `/api/v1/scraper/adapters/${encodeURIComponent(adapterKey)}/fairs`,
  );
}

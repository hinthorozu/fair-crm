import { apiRequest, ApiError, fetchWithTimeout } from "./client";
import { buildApiHeaders, config } from "../config";
import type {
  ScraperDashboardResponse,
  ScraperManifest,
  ScraperManifestListResponse,
  ScraperRun,
  ScraperRunListResponse,
  ScraperRunLogListResponse,
  AdapterDeletePreview,
  AdapterLinkedFairListResponse,
  AdapterListResponse,
  AdapterDetail,
  AdapterEngineListResponse,
  CreateAdapterPayload,
  UpdateAdapterPayload,
  UpdateAdapterManifestPayload,
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

export async function listAdapterEngines(): Promise<AdapterEngineListResponse> {
  return apiRequest<AdapterEngineListResponse>("/api/v1/scraper/engines");
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

export async function getAdapterDeletePreview(adapterKey: string): Promise<AdapterDeletePreview> {
  return apiRequest<AdapterDeletePreview>(
    `/api/v1/scraper/adapters/${encodeURIComponent(adapterKey)}/delete-preview`,
  );
}

export async function deleteAdapter(adapterKey: string): Promise<void> {
  await apiRequest<void>(`/api/v1/scraper/adapters/${encodeURIComponent(adapterKey)}`, {
    method: "DELETE",
  });
}

export async function updateAdapterManifest(
  adapterKey: string,
  payload: UpdateAdapterManifestPayload,
): Promise<ScraperManifest> {
  return apiRequest<ScraperManifest>(
    `/api/v1/scraper/adapters/${encodeURIComponent(adapterKey)}/manifest`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );
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

export async function runAdapterTest(
  adapterKey: string,
  inputUrl: string,
  options?: { outputJson?: boolean; outputExcel?: boolean; maxPages?: number },
): Promise<ScraperRun> {
  const body: {
    input_url: string;
    output_json?: boolean;
    output_excel?: boolean;
    max_pages?: number;
  } = { input_url: inputUrl };
  if (options?.outputJson !== undefined) {
    body.output_json = options.outputJson;
  }
  if (options?.outputExcel !== undefined) {
    body.output_excel = options.outputExcel;
  }
  if (options?.maxPages !== undefined) {
    body.max_pages = options.maxPages;
  }
  return apiRequest<ScraperRun>(
    `/api/v1/scraper/adapters/${encodeURIComponent(adapterKey)}/test-run`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
}

export async function getAdapterLinkedFairs(adapterKey: string): Promise<AdapterLinkedFairListResponse> {
  return apiRequest<AdapterLinkedFairListResponse>(
    `/api/v1/scraper/adapters/${encodeURIComponent(adapterKey)}/fairs`,
  );
}

type ScraperRunOutputKind = "json" | "excel";

async function fetchScraperRunOutput(runId: string, kind: ScraperRunOutputKind): Promise<Blob> {
  const response = await fetchWithTimeout(
    `${config.apiBaseUrl}/api/v1/scraper/runs/${encodeURIComponent(runId)}/output/${kind}`,
    {
      headers: buildApiHeaders({}),
    },
  );
  if (!response.ok) {
    const text = await response.text();
    let detail = `HTTP ${response.status}`;
    try {
      const data = JSON.parse(text) as { detail?: string };
      if (data.detail) detail = data.detail;
    } catch {
      if (text) detail = text;
    }
    throw new ApiError(detail, response.status);
  }
  return response.blob();
}

export async function downloadScraperRunOutput(
  runId: string,
  kind: ScraperRunOutputKind,
  fileName: string,
): Promise<void> {
  const blob = await fetchScraperRunOutput(runId, kind);
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

export async function openScraperRunOutput(runId: string, kind: ScraperRunOutputKind): Promise<void> {
  const blob = await fetchScraperRunOutput(runId, kind);
  const objectUrl = URL.createObjectURL(blob);
  window.open(objectUrl, "_blank", "noopener,noreferrer");
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
}

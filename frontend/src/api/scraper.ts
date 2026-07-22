import { apiRequest, ApiError, fetchWithTimeout } from "./client";
import { buildApiHeaders, config } from "../config";
import { parseContentDispositionFileName, triggerBlobDownload, buildDownloadRequestHeaders } from "../utils/downloadBlob";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import type {
  ScraperDashboardResponse,
  ScraperManifest,
  ScraperManifestListResponse,
  ScraperRun,
  ScraperRunCancelResponse,
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
  ScraperRunStatus,
  AdapterEngineType,
  EnrichmentRunPayload,
  EnrichmentStateResetPayload,
  EnrichmentStateResetResponse,
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
  adapter_key?: string;
  adapter_id?: string;
  status?: ScraperRunStatus;
  engine_type?: AdapterEngineType;
  date_from?: string;
  date_to?: string;
  q?: string;
  url?: string;
}): Promise<ScraperRunListResponse> {
  const search = new URLSearchParams();
  if (params?.limit != null) search.set("limit", String(params.limit));
  if (params?.offset != null) search.set("offset", String(params.offset));
  if (params?.fair_id) search.set("fair_id", params.fair_id);
  if (params?.adapter_key) search.set("adapter_key", params.adapter_key);
  if (params?.adapter_id) search.set("adapter_id", params.adapter_id);
  if (params?.status) search.set("status", params.status);
  if (params?.engine_type) search.set("engine_type", params.engine_type);
  if (params?.date_from) search.set("date_from", params.date_from);
  if (params?.date_to) search.set("date_to", params.date_to);
  if (params?.q) search.set("q", params.q);
  if (params?.url) search.set("url", params.url);
  const qs = search.toString();
  return apiRequest<ScraperRunListResponse>(`/api/v1/scraper/runs${qs ? `?${qs}` : ""}`);
}

export async function listScraperRunsTable(
  params: ServerTableFetchParams,
): Promise<StandardListResponse<ScraperRun>> {
  const limit = params.pageSize;
  const offset = (params.page - 1) * params.pageSize;
  const response = await listScraperRuns({
    limit,
    offset,
    adapter_key: params.filters.adapter_key || undefined,
    status: (params.filters.status as ScraperRunStatus | undefined) || undefined,
    engine_type: (params.filters.engine_type as AdapterEngineType | undefined) || undefined,
    date_from: params.filters.date_from || undefined,
    date_to: params.filters.date_to || undefined,
    q: params.search || params.filters.url || undefined,
  });
  const totalPages = Math.max(1, Math.ceil(response.total / limit));
  return {
    items: response.items,
    pagination: {
      page: params.page,
      pageSize: limit,
      totalItems: response.total,
      totalPages,
      hasNext: params.page < totalPages,
      hasPrevious: params.page > 1,
    },
    sorting: {
      field: params.sortBy ?? "started_at",
      direction: params.sortOrder ?? "desc",
    },
    filters: params.filters,
  };
}

export async function getScraperRun(runId: string): Promise<ScraperRun> {
  return apiRequest<ScraperRun>(`/api/v1/scraper/runs/${encodeURIComponent(runId)}`);
}

export async function cancelScraperRun(runId: string): Promise<ScraperRunCancelResponse> {
  return apiRequest<ScraperRunCancelResponse>(
    `/api/v1/scraper/runs/${encodeURIComponent(runId)}/cancel`,
    { method: "POST" },
  );
}

/** Active-run delete may cooperatively stop the worker (up to ~30s) before hard delete. */
export const DELETE_SCRAPER_RUN_TIMEOUT_MS = 90_000;

export async function deleteScraperRun(runId: string): Promise<void> {
  await apiRequest<void>(
    `/api/v1/scraper/runs/${encodeURIComponent(runId)}`,
    { method: "DELETE" },
    DELETE_SCRAPER_RUN_TIMEOUT_MS,
  );
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

type EnrichmentRunLogExportFormat = "txt" | "json";

const ENRICHMENT_LOG_EXPORT_MIME: Record<EnrichmentRunLogExportFormat, string> = {
  txt: "text/plain",
  json: "application/json",
};

function enrichmentRunLogsExportUrl(runId: string, format: EnrichmentRunLogExportFormat): string {
  const search = new URLSearchParams({ format });
  return `${config.apiBaseUrl}/api/v1/scraper/runs/${encodeURIComponent(runId)}/logs/export?${search.toString()}`;
}

export async function downloadEnrichmentRunLogs(
  runId: string,
  format: EnrichmentRunLogExportFormat,
): Promise<void> {
  const response = await fetchWithTimeout(enrichmentRunLogsExportUrl(runId, format), {
    headers: buildDownloadRequestHeaders(buildApiHeaders({})),
  });
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
  const rawBlob = await response.blob();
  const mimeType = ENRICHMENT_LOG_EXPORT_MIME[format];
  const blob =
    rawBlob.type && rawBlob.type !== "application/octet-stream"
      ? rawBlob
      : new Blob([rawBlob], { type: mimeType });
  const resolvedFileName = parseContentDispositionFileName(
    response.headers.get("Content-Disposition"),
    `fair-crm-enrichment-run.${format}`,
  );
  triggerBlobDownload(blob, resolvedFileName);
}

export async function runCustomerContactEnrichment(
  adapterKey: string,
  payload: EnrichmentRunPayload,
): Promise<ScraperRun> {
  return apiRequest<ScraperRun>(
    `/api/v1/scraper/adapters/${encodeURIComponent(adapterKey)}/enrichment-run`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function resetEnrichmentState(
  payload: EnrichmentStateResetPayload,
): Promise<EnrichmentStateResetResponse> {
  return apiRequest<EnrichmentStateResetResponse>("/api/v1/scraper/enrichment-state/reset", {
    method: "POST",
    body: JSON.stringify(payload),
  });
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

const SCRAPER_OUTPUT_MIME: Record<ScraperRunOutputKind, string> = {
  json: "application/json",
  excel: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
};

function scraperRunOutputUrl(runId: string, kind: ScraperRunOutputKind): string {
  return `${config.apiBaseUrl}/api/v1/scraper/runs/${encodeURIComponent(runId)}/output/${kind}`;
}

function buildScraperDownloadHeaders(): HeadersInit {
  return buildDownloadRequestHeaders(buildApiHeaders({}));
}

async function fetchScraperRunOutput(runId: string, kind: ScraperRunOutputKind): Promise<Response> {
  const response = await fetchWithTimeout(scraperRunOutputUrl(runId, kind), {
    headers: buildScraperDownloadHeaders(),
  });
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
  return response;
}

export async function downloadScraperRunOutput(
  runId: string,
  kind: ScraperRunOutputKind,
  fileName: string,
): Promise<void> {
  const response = await fetchScraperRunOutput(runId, kind);
  const rawBlob = await response.blob();
  const mimeType = SCRAPER_OUTPUT_MIME[kind];
  const blob =
    rawBlob.type && rawBlob.type !== "application/octet-stream"
      ? rawBlob
      : new Blob([rawBlob], { type: mimeType });
  const resolvedFileName = parseContentDispositionFileName(
    response.headers.get("Content-Disposition"),
    fileName,
  );
  triggerBlobDownload(blob, resolvedFileName);
}

export async function openScraperRunOutput(runId: string, kind: ScraperRunOutputKind): Promise<void> {
  const response = await fetchScraperRunOutput(runId, kind);
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  window.open(objectUrl, "_blank", "noopener,noreferrer");
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
}

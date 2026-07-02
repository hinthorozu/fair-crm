import { buildApiHeaders, config } from "../config";
import { normalizeStandardListResponse, buildListQueryParams } from "./listTable";
import { apiRequest, ApiError, ANALYZE_IMPORT_TIMEOUT_MS, fetchWithTimeout } from "./client";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import type {
  ApplyImportResponse,
  BulkDecisionAction,
  ColumnMappingPayload,
  ExcelHeaderMode,
  ImportBatch,
  ImportDecision,
  ImportRow,
  MappingPreviewResponse,
  SetImportRowDecisionPayload,
  UploadRawImportResponse,
} from "../types/import";

export { ApiError };

const BASE = "/api/v1/data-integration/imports";

function authHeadersOnly(): Record<string, string> {
  const built = buildApiHeaders({});
  const headers: Record<string, string> = {};
  if (typeof built === "object" && !Array.isArray(built) && !(built instanceof Headers)) {
    for (const [key, value] of Object.entries(built)) {
      if (key.toLowerCase() !== "content-type") {
        headers[key] = value;
      }
    }
  }
  return headers;
}

export interface ImportBatchListResponse {
  items: ImportBatch[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ImportJobStatus {
  id: string;
  batch_id: string;
  job_type: string;
  status: string;
  progress_processed: number;
  progress_total: number;
  result_json: Record<string, unknown> | null;
  error_message: string | null;
}

export async function listImportBatchesTable(
  params: ServerTableFetchParams,
): Promise<StandardListResponse<ImportBatch>> {
  const qs = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
  });
  const raw = await apiRequest<unknown>(`/api/v1/data-integration/imports?${qs.toString()}`);
  return normalizeStandardListResponse<ImportBatch>(raw);
}

export async function listImportBatches(params: {
  page?: number;
  pageSize?: number;
  sortBy?: string | null;
  sortOrder?: "asc" | "desc" | null;
} = {}): Promise<StandardListResponse<ImportBatch>> {
  const qs = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
  });
  const raw = await apiRequest<unknown>(`/api/v1/data-integration/imports?${qs.toString()}`);
  return normalizeStandardListResponse<ImportBatch>(raw);
}

export async function uploadRawImport(fairId: string, file: File): Promise<UploadRawImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("fair_id", fairId);

  const response = await fetchWithTimeout(`${config.apiBaseUrl}${BASE}/upload`, {
    method: "POST",
    headers: authHeadersOnly(),
    body: formData,
  });

  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    const detail =
      typeof data === "object" && data !== null && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : `HTTP ${response.status}`;
    throw new ApiError(detail, response.status, data);
  }

  return data as UploadRawImportResponse;
}

export async function getMappingPreview(
  batchId: string,
  params: { header_mode?: ExcelHeaderMode; header_row_index?: number } = {},
): Promise<MappingPreviewResponse> {
  const qs = new URLSearchParams();
  if (params.header_mode) qs.set("header_mode", params.header_mode);
  if (params.header_row_index !== undefined) qs.set("header_row_index", String(params.header_row_index));
  const query = qs.toString();
  return apiRequest<MappingPreviewResponse>(
    `${BASE}/${batchId}/mapping-preview${query ? `?${query}` : ""}`,
  );
}

export async function selectImportSheet(
  batchId: string,
  sheetName: string,
): Promise<{
  batch_id: string;
  selected_sheet_name: string;
  suggested_mapping: Record<string, unknown>;
  detected_headers?: (string | null)[];
  mapping_columns?: MappingPreviewResponse["columns"];
  sample_rows?: unknown[][];
}> {
  return apiRequest(`/api/v1/data-integration/imports/${batchId}/sheet`, {
    method: "PATCH",
    body: JSON.stringify({ sheet_name: sheetName }),
  });
}

export async function setColumnMapping(
  batchId: string,
  payload: ColumnMappingPayload,
): Promise<{ batch_id: string; status: string; column_mapping: ColumnMappingPayload }> {
  return apiRequest(`${BASE}/${batchId}/column-mapping`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function configureImportHeader(
  batchId: string,
  payload: {
    has_header_row: boolean;
    header_mode?: ExcelHeaderMode;
    header_row_index?: number | null;
  },
): Promise<{
  batch_id: string;
  status: string;
  header_mode: ExcelHeaderMode;
  header_row_index: number | null;
  has_header_row: boolean;
}> {
  return apiRequest(`${BASE}/${batchId}/header-config`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function startImportAnalyzeJob(batchId: string): Promise<{
  job_id: string;
  batch_id: string;
  status: string;
  progress_total: number;
}> {
  return apiRequest(`/api/v1/data-integration/imports/${batchId}/analyze-job`, { method: "POST" });
}

export async function analyzeImportBatch(batchId: string): Promise<{ batch: ImportBatch; total_rows: number }> {
  const job = await startImportAnalyzeJob(batchId);
  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    const status = await getImportJob(job.job_id);
    if (status.status === "completed" && status.result_json) {
      const batch = await getImportBatch(batchId);
      return {
        batch,
        total_rows: Number(status.result_json.total_rows ?? batch.total_rows ?? 0),
      };
    }
    if (status.status === "failed") {
      throw new ApiError(status.error_message ?? "Analiz başarısız", 500, status);
    }
    await new Promise((r) => window.setTimeout(r, 500));
  }
  throw new ApiError("Analiz zaman aşımına uğradı", 504);
}

export async function bulkAssignRowDecisions(
  batchId: string,
  rowIds: string[],
  decision: ImportDecision,
): Promise<{
  updated_count: number;
  skipped_count: number;
  errors: Array<{ row_id: string; row_number: number; message: string }>;
}> {
  return apiRequest(`${BASE}/${batchId}/rows/bulk-decision`, {
    method: "PATCH",
    body: JSON.stringify({ row_ids: rowIds, decision }),
  });
}

export async function bulkRowDecision(
  batchId: string,
  action: BulkDecisionAction,
): Promise<{ updated_count: number; skipped_count: number; errors: unknown[] }> {
  return apiRequest(`${BASE}/${batchId}/rows/bulk-decision`, {
    method: "PATCH",
    body: JSON.stringify({ action }),
  });
}

export interface BulkDecisionPreview {
  batch_id: string;
  action_type: BulkDecisionAction;
  affected_rows: number;
  already_decided_rows: number;
  summary: string;
  to_process_rows?: number;
  skipped_already_linked_rows?: number;
  unprocessable_rows?: number;
}

export async function previewBulkDecision(
  batchId: string,
  actionType: BulkDecisionAction,
): Promise<BulkDecisionPreview> {
  return apiRequest<BulkDecisionPreview>(`${BASE}/${batchId}/bulk-actions/preview`, {
    method: "POST",
    body: JSON.stringify({ action_type: actionType }),
  });
}

export async function applyImportDecisions(
  batchId: string,
  payload: {
    row_ids?: string[];
    filter?: string;
    search?: string;
  },
): Promise<{
  processed_count: number;
  not_processed_count: number;
  failed_count: number;
  errors: Array<{ row_id: string; row_number: number; message: string }>;
}> {
  return apiRequest(`${BASE}/${batchId}/decisions/apply`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function applyBulkDecisionJob(
  batchId: string,
  actionType: BulkDecisionAction,
): Promise<{ job_id: string; batch_id: string; status: string; progress_total: number }> {
  return apiRequest(`${BASE}/${batchId}/bulk-actions/apply`, {
    method: "POST",
    body: JSON.stringify({ action_type: actionType }),
  });
}

export async function getImportBatch(batchId: string): Promise<ImportBatch> {
  return apiRequest<ImportBatch>(`${BASE}/${batchId}`);
}

export async function deleteImportBatch(batchId: string): Promise<{ batch_id: string; deleted: boolean }> {
  return apiRequest(`${BASE}/${batchId}`, { method: "DELETE" });
}

export async function listImportRows(
  batchId: string,
  params: Partial<ServerTableFetchParams> & { filter?: string } = {},
): Promise<StandardListResponse<ImportRow>> {
  const query = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters: params.filter ? { filter: params.filter } : params.filters,
  });
  const raw = await apiRequest<unknown>(`${BASE}/${batchId}/rows?${query.toString()}`);
  return normalizeStandardListResponse<ImportRow>(raw);
}

export async function setImportRowDecision(
  batchId: string,
  rowId: string,
  payload: SetImportRowDecisionPayload,
): Promise<ImportRow> {
  return apiRequest<ImportRow>(`${BASE}/${batchId}/rows/${rowId}/decision`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function applyImportBatch(batchId: string): Promise<ApplyImportResponse> {
  return apiRequest<ApplyImportResponse>(`${BASE}/${batchId}/apply`, { method: "POST" });
}

export async function startImportApplyJob(batchId: string): Promise<{
  job_id: string;
  batch_id: string;
  status: string;
  progress_total: number;
}> {
  return apiRequest(`/api/v1/data-integration/imports/${batchId}/apply-job`, { method: "POST" });
}

export async function getImportJob(jobId: string): Promise<ImportJobStatus> {
  return apiRequest<ImportJobStatus>(`/api/v1/data-integration/jobs/${jobId}`);
}

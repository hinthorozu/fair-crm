import { buildApiHeaders, config } from "../config";
import { apiRequest, ApiError } from "./client";
import type {
  ApplyImportResponse,
  BulkDecisionAction,
  ColumnMappingPayload,
  ImportBatch,
  ImportRow,
  ImportRowListResponse,
  SetImportRowDecisionPayload,
  UploadRawImportResponse,
} from "../types/import";

export { ApiError };

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

export async function uploadRawImport(fairId: string, file: File): Promise<UploadRawImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("fair_id", fairId);

  const response = await fetch(`${config.apiBaseUrl}/api/v1/imports/upload`, {
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

export async function setColumnMapping(
  batchId: string,
  payload: ColumnMappingPayload,
): Promise<{ batch_id: string; status: string; column_mapping: ColumnMappingPayload }> {
  return apiRequest(`/api/v1/imports/${batchId}/column-mapping`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function analyzeImportBatch(batchId: string): Promise<{ batch: ImportBatch; total_rows: number }> {
  return apiRequest(`/api/v1/imports/${batchId}/analyze`, { method: "POST" });
}

export async function bulkRowDecision(
  batchId: string,
  action: BulkDecisionAction,
): Promise<{ updated_count: number }> {
  return apiRequest(`/api/v1/imports/${batchId}/rows/bulk-decision`, {
    method: "PATCH",
    body: JSON.stringify({ action }),
  });
}

export async function getImportBatch(batchId: string): Promise<ImportBatch> {
  return apiRequest<ImportBatch>(`/api/v1/imports/${batchId}`);
}

export async function listImportRows(
  batchId: string,
  params?: {
    filter?: string;
    search?: string;
    sort_by?: string;
    sort_dir?: "asc" | "desc";
  },
): Promise<ImportRowListResponse> {
  const query = new URLSearchParams();
  if (params?.filter) query.set("filter", params.filter);
  if (params?.search) query.set("search", params.search);
  if (params?.sort_by) query.set("sort_by", params.sort_by);
  if (params?.sort_dir) query.set("sort_dir", params.sort_dir);
  const qs = query.toString();
  return apiRequest<ImportRowListResponse>(
    `/api/v1/imports/${batchId}/rows${qs ? `?${qs}` : ""}`,
  );
}

export async function setImportRowDecision(
  batchId: string,
  rowId: string,
  payload: SetImportRowDecisionPayload,
): Promise<ImportRow> {
  return apiRequest<ImportRow>(`/api/v1/imports/${batchId}/rows/${rowId}/decision`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function applyImportBatch(batchId: string): Promise<ApplyImportResponse> {
  return apiRequest<ApplyImportResponse>(`/api/v1/imports/${batchId}/apply`, {
    method: "POST",
  });
}

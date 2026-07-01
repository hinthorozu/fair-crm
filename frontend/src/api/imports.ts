import { buildApiHeaders, config } from "../config";
import { apiRequest, ApiError } from "./client";
import type {
  ApplyImportResponse,
  ImportBatch,
  ImportRow,
  ImportRowListResponse,
  SetImportRowDecisionPayload,
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

export async function uploadCustomerImport(file: File): Promise<ImportBatch> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${config.apiBaseUrl}/api/v1/imports/customers/upload`, {
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

  return data as ImportBatch;
}

export async function getImportBatch(batchId: string): Promise<ImportBatch> {
  return apiRequest<ImportBatch>(`/api/v1/imports/${batchId}`);
}

export async function listImportRows(batchId: string): Promise<ImportRowListResponse> {
  return apiRequest<ImportRowListResponse>(`/api/v1/imports/${batchId}/rows`);
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

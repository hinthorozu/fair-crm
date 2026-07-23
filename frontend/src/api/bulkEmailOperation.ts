import { buildApiHeaders, config } from "../config";
import { ApiError, apiRequest, fetchWithTimeout } from "./client";
import type {
  BulkEmailOperationExportFormat,
  BulkEmailOperationLogsResponse,
  BulkEmailOperationPreviewResponse,
  BulkEmailOperationRecipientsResponse,
  BulkEmailOperationSendResponse,
  PreviewBulkEmailOperationPayload,
  SendBulkEmailOperationPayload,
} from "../types/bulkEmailOperation";
import {
  buildDownloadRequestHeaders,
  parseContentDispositionFileName,
  triggerBlobDownload,
} from "../utils/downloadBlob";
import type { Operation } from "../types/operation";

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

async function parseJsonResponse<T>(response: Response): Promise<T> {
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

  return data as T;
}

function appendBulkEmailFormPayload(
  formData: FormData,
  payload: Omit<PreviewBulkEmailOperationPayload, "excel_file"> | Omit<SendBulkEmailOperationPayload, "excel_file">,
  mode: "preview" | "send",
): void {
  const recipientOptions = payload.recipient_options ?? {
    include_customer_emails: true,
    include_contact_emails: true,
    skip_no_email: true,
    exclude_inactive: true,
    dedupe_emails: true,
  };

  if (mode === "preview") {
    const preview = payload as Omit<PreviewBulkEmailOperationPayload, "excel_file">;
    formData.append(
      "payload",
      JSON.stringify({
        source_type: preview.source_type,
        template_id: preview.template_id,
        smtp_account_id: preview.smtp_account_id,
        subject_override: preview.subject_override,
        manual_emails: preview.manual_emails ?? null,
        fair_ids: preview.fair_ids ?? [],
        country_filter: preview.country_filter ?? null,
        city_filter: preview.city_filter ?? null,
        company_name_contains: preview.company_name_contains ?? null,
        recipient_options: recipientOptions,
      }),
    );
    return;
  }

  const send = payload as Omit<SendBulkEmailOperationPayload, "excel_file">;
  formData.append(
    "payload",
    JSON.stringify({
      source_type: send.source_type,
      template_id: send.template_id,
      smtp_account_id: send.smtp_account_id,
      subject: send.subject,
      title: send.title ?? null,
      manual_emails: send.manual_emails ?? null,
      fair_ids: send.fair_ids ?? [],
      country_filter: send.country_filter ?? null,
      city_filter: send.city_filter ?? null,
      company_name_contains: send.company_name_contains ?? null,
      recipient_options: recipientOptions,
      client_token: send.client_token ?? null,
    }),
  );
}

export async function previewBulkEmailOperation(
  payload: PreviewBulkEmailOperationPayload,
): Promise<BulkEmailOperationPreviewResponse> {
  const formData = new FormData();
  const { excel_file, ...jsonPayload } = payload;
  appendBulkEmailFormPayload(formData, jsonPayload, "preview");
  if (excel_file) {
    formData.append("excel_file", excel_file);
  }

  const response = await fetchWithTimeout(
    `${config.apiBaseUrl}/api/v1/operations/bulk-email/preview`,
    {
      method: "POST",
      headers: authHeadersOnly(),
      body: formData,
    },
  );

  return parseJsonResponse<BulkEmailOperationPreviewResponse>(response);
}

export async function sendBulkEmailOperation(
  payload: SendBulkEmailOperationPayload,
): Promise<BulkEmailOperationSendResponse> {
  const formData = new FormData();
  const { excel_file, ...jsonPayload } = payload;
  appendBulkEmailFormPayload(formData, jsonPayload, "send");
  if (excel_file) {
    formData.append("excel_file", excel_file);
  }

  const response = await fetchWithTimeout(
    `${config.apiBaseUrl}/api/v1/operations/bulk-email/send`,
    {
      method: "POST",
      headers: authHeadersOnly(),
      body: formData,
    },
  );

  return parseJsonResponse<BulkEmailOperationSendResponse>(response);
}

export function listBulkEmailOperationRecipients(
  operationId: string,
): Promise<BulkEmailOperationRecipientsResponse> {
  return apiRequest<BulkEmailOperationRecipientsResponse>(
    `/api/v1/operations/${encodeURIComponent(operationId)}/bulk-email/recipients`,
  );
}

export function listBulkEmailOperationLogs(
  operationId: string,
): Promise<BulkEmailOperationLogsResponse> {
  return apiRequest<BulkEmailOperationLogsResponse>(
    `/api/v1/operations/${encodeURIComponent(operationId)}/bulk-email/logs`,
  );
}

export function retryBulkEmailOperationFailed(operationId: string): Promise<Operation> {
  return apiRequest<Operation>(
    `/api/v1/operations/${encodeURIComponent(operationId)}/bulk-email/retry-failed`,
    { method: "POST" },
  );
}

const BULK_EMAIL_EXPORT_MIME: Record<BulkEmailOperationExportFormat, string> = {
  json: "application/json",
  excel: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
};

function bulkEmailExportUrl(operationId: string, format: BulkEmailOperationExportFormat): string {
  const qs = new URLSearchParams({ format });
  return `${config.apiBaseUrl}/api/v1/operations/${encodeURIComponent(operationId)}/bulk-email/export?${qs.toString()}`;
}

async function fetchBulkEmailOperationExport(
  operationId: string,
  format: BulkEmailOperationExportFormat,
): Promise<Response> {
  const response = await fetchWithTimeout(bulkEmailExportUrl(operationId, format), {
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
  return response;
}

export async function downloadBulkEmailOperationExport(
  operationId: string,
  format: BulkEmailOperationExportFormat,
  fileName?: string,
): Promise<void> {
  const response = await fetchBulkEmailOperationExport(operationId, format);
  const rawBlob = await response.blob();
  const mimeType = BULK_EMAIL_EXPORT_MIME[format];
  const blob =
    rawBlob.type && rawBlob.type !== "application/octet-stream"
      ? rawBlob
      : new Blob([rawBlob], { type: mimeType });
  const fallback =
    fileName ??
    `bulk-email-${operationId}.${format === "json" ? "json" : "xlsx"}`;
  const resolvedFileName = parseContentDispositionFileName(
    response.headers.get("Content-Disposition"),
    fallback,
  );
  triggerBlobDownload(blob, resolvedFileName);
}

export async function openBulkEmailOperationExport(
  operationId: string,
  format: BulkEmailOperationExportFormat,
): Promise<void> {
  const response = await fetchBulkEmailOperationExport(operationId, format);
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  window.open(objectUrl, "_blank", "noopener,noreferrer");
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
}

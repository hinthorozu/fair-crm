import { normalizeStandardListResponse, buildListQueryParams } from "./listTable";
import { apiRequest, ApiError } from "./client";
import type { StandardListResponse } from "../types/listTable";
import type { ListMailOperationsParams, MailOperationRecord } from "../types/mailOperations";

export async function listMailOperations(
  params: ListMailOperationsParams = {},
): Promise<StandardListResponse<MailOperationRecord>> {
  const filters: Record<string, string> = {};
  if (params.status && params.status !== "all") filters.status = params.status;
  if (params.sourceType && params.sourceType !== "all") filters.source_type = params.sourceType;
  if (params.smtpAccountId && params.smtpAccountId !== "all") {
    filters.smtp_account_id = params.smtpAccountId;
  }
  if (params.fairId && params.fairId !== "all") filters.fair_id = params.fairId;
  if (params.dateFrom) filters.date_from = params.dateFrom;
  if (params.dateTo) filters.date_to = params.dateTo;

  const query = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    filters,
  });
  const raw = await apiRequest<unknown>(`/api/v1/mail-send-operations?${query.toString()}`);
  return normalizeStandardListResponse<MailOperationRecord>(raw);
}

export interface RetryMailOperationResponse {
  success: boolean;
  operation: MailOperationRecord;
}

export async function retryMailOperation(operationId: string): Promise<RetryMailOperationResponse> {
  return apiRequest<RetryMailOperationResponse>(
    `/api/v1/mail-send-operations/${encodeURIComponent(operationId)}/retry`,
    { method: "POST" },
  );
}

export { ApiError };

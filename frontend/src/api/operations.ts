import { normalizeStandardListResponse, buildListQueryParams } from "./listTable";
import { apiRequest } from "./client";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import type {
  CreateOperationPayload,
  Operation,
  OperationDetail,
  OperationRun,
  WizardMetadata,
} from "../types/operation";

export interface ListOperationsParams extends Partial<ServerTableFetchParams> {
  operation_type?: string;
  status?: string;
}

export async function getOperationWizardMetadata(): Promise<WizardMetadata> {
  return apiRequest<WizardMetadata>("/api/v1/operations/wizard-metadata");
}

export async function listOperations(
  params: ListOperationsParams = {},
): Promise<StandardListResponse<Operation>> {
  const filters: Record<string, string | undefined> = { ...params.filters };
  const operationType = params.operation_type ?? filters.operation_type;
  const status = params.status ?? filters.status;
  if (operationType) filters.operation_type = operationType;
  if (status) filters.status = status;

  const query = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters,
  });
  const raw = await apiRequest<unknown>(`/api/v1/operations?${query.toString()}`);
  return normalizeStandardListResponse<Operation>(raw);
}

export function getOperation(id: string): Promise<OperationDetail> {
  return apiRequest<OperationDetail>(`/api/v1/operations/${id}`);
}

export function createOperation(payload: CreateOperationPayload): Promise<Operation> {
  return apiRequest<Operation>("/api/v1/operations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function startOperation(id: string): Promise<Operation> {
  return apiRequest<Operation>(`/api/v1/operations/${id}/start`, { method: "POST" });
}

export function cancelOperation(id: string, runId?: string): Promise<Operation> {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  return apiRequest<Operation>(`/api/v1/operations/${id}/cancel${query}`, {
    method: "POST",
  });
}

export function retryOperation(id: string, runId?: string): Promise<Operation> {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  return apiRequest<Operation>(`/api/v1/operations/${id}/retry${query}`, {
    method: "POST",
  });
}

export async function listOperationRuns(
  operationId: string,
  params: Partial<ServerTableFetchParams> = {},
): Promise<StandardListResponse<OperationRun>> {
  const query = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
  });
  const raw = await apiRequest<unknown>(
    `/api/v1/operations/${operationId}/runs?${query.toString()}`,
  );
  return normalizeStandardListResponse<OperationRun>(raw);
}

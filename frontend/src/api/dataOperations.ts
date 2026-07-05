import { buildApiHeaders, config } from "../config";
import { apiRequest, ApiError, fetchWithTimeout, DUPLICATE_GROUPS_LIST_TIMEOUT_MS } from "./client";
import { normalizeStandardListResponse, buildListQueryParams } from "./listTable";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import type { Customer, CustomerStatus, CustomerType } from "../types/customer";
import type {
  AssignCustomersToFairResponse,
  DeleteSelectedCustomersResponse,
  DataOperationDefinition,
  DataOperationRun,
  DataOperationsListResponse,
  DuplicateDatasetCustomer,
  DuplicateDatasetGroup,
  DuplicateDatasetGroupDetail,
  DuplicateGroupMergePreview,
  DuplicateGroupMergePreviewRequest,
  DuplicateGroupMergeExecuteResponse,
  DuplicateGroupMergeExecuteRequest,
  RunDataOperationRequest,
  RunDataOperationResponse,
} from "../types/dataOperations";

export { ApiError };

export async function listDataOperations(): Promise<DataOperationDefinition[]> {
  const response = await apiRequest<DataOperationsListResponse>("/api/v1/admin/data-operations");
  return response.items;
}

export async function runDataOperation(
  operationKey: string,
  payload?: RunDataOperationRequest,
): Promise<RunDataOperationResponse> {
  return apiRequest<RunDataOperationResponse>(`/api/v1/admin/data-operations/${operationKey}/run`, {
    method: "POST",
    body: payload ? JSON.stringify(payload) : undefined,
  });
}

export async function getDataOperationRun(runId: string): Promise<DataOperationRun> {
  return apiRequest<DataOperationRun>(`/api/v1/admin/data-operations/runs/${runId}`);
}

export async function assignCustomersToFair(
  runId: string,
  payload: { fair_id: string; customer_ids: string[] },
): Promise<AssignCustomersToFairResponse> {
  return apiRequest(`/api/v1/admin/data-operations/runs/${runId}/assign-fair`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteSelectedCustomers(
  runId: string,
  payload: { customer_ids: string[] },
): Promise<DeleteSelectedCustomersResponse> {
  return apiRequest(`/api/v1/admin/data-operations/runs/${runId}/delete-customers`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listDataOperationDatasetCustomers(
  runId: string,
  params: ServerTableFetchParams & {
    status?: CustomerStatus;
    customer_type?: CustomerType;
    country?: string;
  },
): Promise<StandardListResponse<Customer>> {
  const qs = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters: {
      ...(params.status ? { status: params.status } : {}),
      ...(params.customer_type ? { customer_type: params.customer_type } : {}),
      ...(params.country ? { country: params.country } : {}),
      ...params.filters,
    },
  });
  const raw = await apiRequest<unknown>(
    `/api/v1/admin/data-operations/runs/${runId}/dataset/customers?${qs.toString()}`,
  );
  return normalizeStandardListResponse<Customer>(raw);
}

export async function exportDataOperationDatasetCustomers(
  runId: string,
  params: Partial<ServerTableFetchParams> & {
    status?: CustomerStatus;
    customer_type?: CustomerType;
    country?: string;
  } = {},
): Promise<void> {
  const qs = buildListQueryParams({
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters: {
      ...(params.status ? { status: params.status } : {}),
      ...(params.customer_type ? { customer_type: params.customer_type } : {}),
      ...(params.country ? { country: params.country } : {}),
      ...params.filters,
    },
  });
  const response = await fetchWithTimeout(
    `${config.apiBaseUrl}/api/v1/admin/data-operations/runs/${runId}/dataset/customers/export?${qs.toString()}`,
    { headers: buildApiHeaders({}) },
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
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const fileName = match?.[1] ?? "customers_without_fair.xlsx";
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

export async function listDataOperationDuplicateCustomers(
  runId: string,
  params: ServerTableFetchParams & {
    status?: CustomerStatus;
    customer_type?: CustomerType;
    country?: string;
  },
): Promise<StandardListResponse<DuplicateDatasetCustomer>> {
  const qs = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters: {
      ...(params.status ? { status: params.status } : {}),
      ...(params.customer_type ? { customer_type: params.customer_type } : {}),
      ...(params.country ? { country: params.country } : {}),
      ...params.filters,
    },
  });
  const raw = await apiRequest<unknown>(
    `/api/v1/admin/data-operations/runs/${runId}/dataset/duplicate-customers?${qs.toString()}`,
  );
  return normalizeStandardListResponse<DuplicateDatasetCustomer>(raw);
}

export async function listDataOperationDuplicateGroups(
  runId: string,
  params: ServerTableFetchParams,
): Promise<StandardListResponse<DuplicateDatasetGroup>> {
  const qs = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters: params.filters,
  });
  const raw = await apiRequest<unknown>(
    `/api/v1/admin/data-operations/runs/${runId}/dataset/duplicate-groups?${qs.toString()}`,
    undefined,
    DUPLICATE_GROUPS_LIST_TIMEOUT_MS,
  );
  return normalizeStandardListResponse<DuplicateDatasetGroup>(raw);
}

export async function getDataOperationDuplicateGroupDetail(
  runId: string,
  duplicateGroupKey: string,
): Promise<DuplicateDatasetGroupDetail> {
  return apiRequest<DuplicateDatasetGroupDetail>(
    `/api/v1/admin/data-operations/runs/${runId}/dataset/duplicate-groups/${encodeURIComponent(duplicateGroupKey)}`,
  );
}

export async function previewDuplicateGroupMerge(
  groupKey: string,
  payload: DuplicateGroupMergePreviewRequest,
): Promise<DuplicateGroupMergePreview> {
  return apiRequest<DuplicateGroupMergePreview>(
    `/api/v1/admin/data-operations/duplicate-groups/${encodeURIComponent(groupKey)}/merge-preview`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function executeDuplicateGroupMerge(
  groupKey: string,
  payload: DuplicateGroupMergeExecuteRequest,
): Promise<DuplicateGroupMergeExecuteResponse> {
  return apiRequest<DuplicateGroupMergeExecuteResponse>(
    `/api/v1/admin/data-operations/duplicate-groups/${encodeURIComponent(groupKey)}/merge-execute`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    120_000,
  );
}

export async function exportDataOperationDuplicateCustomers(
  runId: string,
  params: Partial<ServerTableFetchParams> & {
    status?: CustomerStatus;
    customer_type?: CustomerType;
    country?: string;
  } = {},
): Promise<void> {
  const qs = buildListQueryParams({
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters: {
      ...(params.status ? { status: params.status } : {}),
      ...(params.customer_type ? { customer_type: params.customer_type } : {}),
      ...(params.country ? { country: params.country } : {}),
      ...params.filters,
    },
  });
  const response = await fetchWithTimeout(
    `${config.apiBaseUrl}/api/v1/admin/data-operations/runs/${runId}/dataset/duplicate-customers/export?${qs.toString()}`,
    { headers: buildApiHeaders({}) },
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
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const fileName = match?.[1] ?? "customer_duplicates.xlsx";
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

export async function downloadDataOperationFile(
  runId: string,
  fileId: string,
  fileName: string,
): Promise<void> {
  const response = await fetchWithTimeout(
    `${config.apiBaseUrl}/api/v1/admin/data-operations/runs/${runId}/files/${fileId}/download`,
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
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

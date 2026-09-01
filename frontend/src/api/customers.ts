import { normalizeStandardListResponse, buildListQueryParams } from "./listTable";
import { apiRequest, ApiError, formatApiErrorMessage, fetchWithTimeout } from "./client";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import type {
  CreateCustomerPayload,
  Customer,
  UpdateCustomerPayload,
} from "../types/customer";
import type { CustomerStatus, CustomerType } from "../types/customer";
import { buildApiHeaders, config } from "../config";
import { CUSTOMER_READ } from "../permissions/customerPermissions";
import { getGrantedCorePermissions } from "../permissions/corePermissions";
import {
  buildDownloadRequestHeaders,
  parseContentDispositionFileName,
  triggerBlobDownload,
} from "../utils/downloadBlob";

const CUSTOMER_READ_DENIED = `Müşteri bilgilerini görüntüleme yetkiniz yok (${CUSTOMER_READ}).`;

export interface ListCustomersParams extends Partial<ServerTableFetchParams> {
  status?: CustomerStatus;
  customer_type?: CustomerType;
  country?: string;
  missing_info?: string;
}

export async function listCustomers(
  params: ListCustomersParams = {},
): Promise<StandardListResponse<Customer>> {
  if (!getGrantedCorePermissions().has(CUSTOMER_READ)) {
    throw new ApiError(CUSTOMER_READ_DENIED, 403);
  }
  const query = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters: {
      ...(params.status ? { status: params.status } : {}),
      ...(params.customer_type ? { customer_type: params.customer_type } : {}),
      ...(params.country ? { country: params.country } : {}),
      ...(params.missing_info ? { missing_info: params.missing_info } : {}),
      ...params.filters,
    },
  });
  const raw = await apiRequest<unknown>(`/api/v1/customers?${query.toString()}`);
  return normalizeStandardListResponse<Customer>(raw);
}

export async function exportCustomers(params: ListCustomersParams = {}): Promise<void> {
  if (!getGrantedCorePermissions().has(CUSTOMER_READ)) {
    throw new ApiError(CUSTOMER_READ_DENIED, 403);
  }
  const query = buildListQueryParams({
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters: {
      ...(params.status ? { status: params.status } : {}),
      ...(params.customer_type ? { customer_type: params.customer_type } : {}),
      ...(params.country ? { country: params.country } : {}),
      ...(params.missing_info ? { missing_info: params.missing_info } : {}),
      ...params.filters,
    },
  });
  const response = await fetchWithTimeout(
    `${config.apiBaseUrl}/api/v1/customers/export?${query.toString()}`,
    { headers: buildDownloadRequestHeaders(buildApiHeaders({})) },
    120_000,
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
  const fileName = parseContentDispositionFileName(
    response.headers.get("Content-Disposition"),
    "customers.xlsx",
  );
  triggerBlobDownload(blob, fileName);
}

export function getCustomer(id: string): Promise<Customer> {
  if (!getGrantedCorePermissions().has(CUSTOMER_READ)) {
    return Promise.reject(new ApiError(CUSTOMER_READ_DENIED, 403));
  }
  return apiRequest<Customer>(`/api/v1/customers/${id}`);
}

export function createCustomer(payload: CreateCustomerPayload): Promise<Customer> {
  return apiRequest<Customer>("/api/v1/customers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCustomer(id: string, payload: UpdateCustomerPayload): Promise<Customer> {
  return apiRequest<Customer>(`/api/v1/customers/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function archiveCustomer(id: string): Promise<Customer> {
  return apiRequest<Customer>(`/api/v1/customers/${id}`, {
    method: "DELETE",
  });
}

export function restoreCustomer(id: string): Promise<Customer> {
  const customerId = id?.trim();
  if (!customerId) {
    return Promise.reject(new ApiError("Müşteri kimliği eksik.", 400));
  }
  return apiRequest<Customer>(`/api/v1/customers/${encodeURIComponent(customerId)}/restore`, {
    method: "POST",
  });
}

export { ApiError, formatApiErrorMessage };

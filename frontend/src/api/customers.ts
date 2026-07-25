import { normalizeStandardListResponse, buildListQueryParams } from "./listTable";
import { apiRequest, ApiError, formatApiErrorMessage } from "./client";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import type {
  CreateCustomerPayload,
  Customer,
  UpdateCustomerPayload,
} from "../types/customer";
import type { CustomerStatus, CustomerType } from "../types/customer";

export interface ListCustomersParams extends Partial<ServerTableFetchParams> {
  status?: CustomerStatus;
  customer_type?: CustomerType;
  country?: string;
}

export async function listCustomers(
  params: ListCustomersParams = {},
): Promise<StandardListResponse<Customer>> {
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
      ...params.filters,
    },
  });
  const raw = await apiRequest<unknown>(`/api/v1/customers?${query.toString()}`);
  return normalizeStandardListResponse<Customer>(raw);
}

export function getCustomer(id: string): Promise<Customer> {
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

import { normalizePaginatedResponse } from "./pagination";
import { apiRequest, ApiError, formatApiErrorMessage } from "./client";
import type {
  CreateCustomerPayload,
  Customer,
  CustomerListResponse,
  ListCustomersParams,
  UpdateCustomerPayload,
} from "../types/customer";
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE } from "../types/pagination";

function buildQuery(params: ListCustomersParams): string {
  const q = new URLSearchParams();
  if (params.search) q.set("search", params.search);
  if (params.status) q.set("status", params.status);
  if (params.customer_type) q.set("customer_type", params.customer_type);
  q.set("page", String(params.page ?? DEFAULT_PAGE));
  q.set("page_size", String(params.page_size ?? DEFAULT_PAGE_SIZE));
  if (params.sort_by) q.set("sort_by", params.sort_by);
  if (params.sort_dir) q.set("sort_dir", params.sort_dir);
  return `?${q.toString()}`;
}

export async function listCustomers(params: ListCustomersParams = {}): Promise<CustomerListResponse> {
  const page = params.page ?? DEFAULT_PAGE;
  const page_size = params.page_size ?? DEFAULT_PAGE_SIZE;
  const raw = await apiRequest<unknown>(`/api/v1/customers${buildQuery(params)}`);
  return normalizePaginatedResponse<Customer>(raw, { page, page_size });
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

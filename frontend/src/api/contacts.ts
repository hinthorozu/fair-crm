import { normalizePaginatedResponse } from "./pagination";
import { apiRequest } from "./client";
import type {
  Contact,
  ContactListResponse,
  CreateContactPayload,
  ListContactsParams,
  UpdateContactPayload,
} from "../types/contact";
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE } from "../types/pagination";

function buildQuery(params: ListContactsParams): string {
  const q = new URLSearchParams();
  q.set("page", String(params.page ?? DEFAULT_PAGE));
  q.set("page_size", String(params.page_size ?? DEFAULT_PAGE_SIZE));
  if (params.sort_by) q.set("sort_by", params.sort_by);
  if (params.sort_dir) q.set("sort_dir", params.sort_dir);
  return `?${q.toString()}`;
}

export async function listContactsByCustomer(
  customerId: string,
  params: ListContactsParams = {},
): Promise<ContactListResponse> {
  const page = params.page ?? DEFAULT_PAGE;
  const page_size = params.page_size ?? DEFAULT_PAGE_SIZE;
  const raw = await apiRequest<unknown>(
    `/api/v1/customers/${encodeURIComponent(customerId)}/contacts${buildQuery(params)}`,
  );
  return normalizePaginatedResponse<Contact>(raw, { page, page_size });
}

export function getContact(id: string): Promise<Contact> {
  return apiRequest<Contact>(`/api/v1/contacts/${encodeURIComponent(id)}`);
}

export function createContact(payload: CreateContactPayload): Promise<Contact> {
  return apiRequest<Contact>("/api/v1/contacts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateContact(id: string, payload: UpdateContactPayload): Promise<Contact> {
  return apiRequest<Contact>(`/api/v1/contacts/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteContact(id: string): Promise<Contact> {
  return apiRequest<Contact>(`/api/v1/contacts/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

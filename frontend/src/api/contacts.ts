import { normalizeStandardListResponse, buildListQueryParams } from "./listTable";
import { apiRequest } from "./client";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import type {
  Contact,
  CreateContactPayload,
  UpdateContactPayload,
} from "../types/contact";

export type ListContactsParams = Partial<ServerTableFetchParams>;

export async function listContactsByCustomer(
  customerId: string,
  params: ListContactsParams = {},
): Promise<StandardListResponse<Contact>> {
  const query = buildListQueryParams(params);
  const raw = await apiRequest<unknown>(
    `/api/v1/customers/${encodeURIComponent(customerId)}/contacts?${query.toString()}`,
  );
  return normalizeStandardListResponse<Contact>(raw);
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

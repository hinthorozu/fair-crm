import { normalizePaginatedResponse } from "./pagination";
import { apiRequest } from "./client";
import type {
  CreateParticipationPayload,
  CustomerParticipationListResponse,
  FairParticipantListResponse,
  ListParticipationsParams,
  Participation,
  UpdateParticipationPayload,
} from "../types/participation";
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE } from "../types/pagination";

function buildQuery(params: ListParticipationsParams): string {
  const q = new URLSearchParams();
  q.set("page", String(params.page ?? DEFAULT_PAGE));
  q.set("page_size", String(params.page_size ?? DEFAULT_PAGE_SIZE));
  if (params.sort_by) q.set("sort_by", params.sort_by);
  if (params.sort_dir) q.set("sort_dir", params.sort_dir);
  return `?${q.toString()}`;
}

export async function listParticipationsByCustomer(
  customerId: string,
  params: ListParticipationsParams = {},
): Promise<CustomerParticipationListResponse> {
  const page = params.page ?? DEFAULT_PAGE;
  const page_size = params.page_size ?? DEFAULT_PAGE_SIZE;
  const raw = await apiRequest<unknown>(
    `/api/v1/customers/${customerId}/fair-participations${buildQuery(params)}`,
  );
  return normalizePaginatedResponse(raw, { page, page_size });
}

export async function listParticipantsByFair(
  fairId: string,
  params: ListParticipationsParams = {},
): Promise<FairParticipantListResponse> {
  const page = params.page ?? DEFAULT_PAGE;
  const page_size = params.page_size ?? DEFAULT_PAGE_SIZE;
  const raw = await apiRequest<unknown>(
    `/api/v1/fairs/${fairId}/participants${buildQuery(params)}`,
  );
  return normalizePaginatedResponse(raw, { page, page_size });
}

export function createParticipation(payload: CreateParticipationPayload): Promise<Participation> {
  return apiRequest<Participation>("/api/v1/fair-participations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateParticipation(
  id: string,
  payload: UpdateParticipationPayload,
): Promise<Participation> {
  return apiRequest<Participation>(`/api/v1/fair-participations/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteParticipation(id: string): Promise<Participation> {
  return apiRequest<Participation>(`/api/v1/fair-participations/${id}`, {
    method: "DELETE",
  });
}

export function getParticipation(id: string): Promise<Participation> {
  return apiRequest<Participation>(`/api/v1/fair-participations/${id}`);
}

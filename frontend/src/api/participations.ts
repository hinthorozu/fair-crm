import { normalizeStandardListResponse, buildListQueryParams } from "./listTable";
import { apiRequest } from "./client";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import type {
  CreateParticipationPayload,
  CustomerParticipationListItem,
  FairParticipantListItem,
  Participation,
  UpdateParticipationPayload,
} from "../types/participation";

export interface ListParticipationsParams extends Partial<ServerTableFetchParams> {
  participationStatus?: string;
}

export async function listParticipationsByCustomer(
  customerId: string,
  params: ListParticipationsParams = {},
): Promise<StandardListResponse<CustomerParticipationListItem>> {
  const query = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters: {
      ...(params.participationStatus ? { participationStatus: params.participationStatus } : {}),
      ...params.filters,
    },
  });
  const raw = await apiRequest<unknown>(
    `/api/v1/customers/${customerId}/fair-participations?${query.toString()}`,
  );
  return normalizeStandardListResponse<CustomerParticipationListItem>(raw);
}

export async function listParticipantsByFair(
  fairId: string,
  params: ListParticipationsParams = {},
): Promise<StandardListResponse<FairParticipantListItem>> {
  const query = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters: {
      ...(params.participationStatus ? { participationStatus: params.participationStatus } : {}),
      ...params.filters,
    },
  });
  const raw = await apiRequest<unknown>(`/api/v1/fairs/${fairId}/participants?${query.toString()}`);
  return normalizeStandardListResponse<FairParticipantListItem>(raw);
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

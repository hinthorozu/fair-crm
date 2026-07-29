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

export type ListParticipationsParams = Partial<ServerTableFetchParams>;

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
    filters: params.filters,
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
    filters: params.filters,
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

export interface MoveParticipantsToFairResult {
  source_fair_id: string;
  target_fair_id: string;
  moved_count: number;
  already_on_target_count: number;
  source_remaining: number;
}

export function moveParticipantsToFair(
  sourceFairId: string,
  targetFairId: string,
): Promise<MoveParticipantsToFairResult> {
  return apiRequest<MoveParticipantsToFairResult>(
    `/api/v1/fairs/${sourceFairId}/participants/move-to-fair`,
    {
      method: "POST",
      body: JSON.stringify({ target_fair_id: targetFairId }),
    },
  );
}

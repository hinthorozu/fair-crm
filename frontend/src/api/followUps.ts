import { buildListQueryParams, normalizeStandardListResponse } from "./listTable";
import { apiRequest } from "./client";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import type { FollowUpFilter, FollowUpRow } from "../types/followUps";

export interface ListFollowUpsParams extends Partial<ServerTableFetchParams> {
  filter?: FollowUpFilter;
}

export async function listFollowUps(
  params: ListFollowUpsParams = {},
): Promise<StandardListResponse<FollowUpRow>> {
  const filters: Record<string, string | undefined> = { ...params.filters };
  const filter = params.filter ?? filters.filter ?? "bugun";
  filters.filter = filter;

  const query = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters,
  });
  const raw = await apiRequest<unknown>(`/api/v1/follow-ups?${query.toString()}`);
  return normalizeStandardListResponse<FollowUpRow>(raw);
}

import { buildApiHeaders, config } from "../config";
import { apiRequest, ApiError, fetchWithTimeout } from "./client";
import { normalizeStandardListResponse, buildListQueryParams } from "./listTable";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import type { BackupFormat, CreateSystemBackupResponse, SystemBackup } from "../types/systemBackup";

export { ApiError };

export async function listSystemBackupsTable(
  params: ServerTableFetchParams,
): Promise<StandardListResponse<SystemBackup>> {
  const qs = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
  });
  const raw = await apiRequest<unknown>(`/api/v1/admin/backups?${qs.toString()}`);
  return normalizeStandardListResponse<SystemBackup>(raw);
}

export async function listSystemBackups(params?: {
  page?: number;
  page_size?: number;
  sortBy?: string | null;
  sortOrder?: "asc" | "desc" | null;
}): Promise<StandardListResponse<SystemBackup>> {
  const qs = buildListQueryParams({
    page: params?.page,
    pageSize: params?.page_size,
    sortBy: params?.sortBy,
    sortOrder: params?.sortOrder,
  });
  const raw = await apiRequest<unknown>(`/api/v1/admin/backups?${qs.toString()}`);
  return normalizeStandardListResponse<SystemBackup>(raw);
}

export async function createSystemBackup(
  notes?: string | null,
  backupFormat: BackupFormat = "postgresql_dump",
): Promise<CreateSystemBackupResponse> {
  return apiRequest<CreateSystemBackupResponse>("/api/v1/admin/backups", {
    method: "POST",
    body: JSON.stringify({ notes: notes ?? null, backup_format: backupFormat }),
  });
}

export async function getSystemBackup(id: string): Promise<SystemBackup> {
  return apiRequest<SystemBackup>(`/api/v1/admin/backups/${id}`);
}

export async function downloadSystemBackup(id: string, fileName: string): Promise<void> {
  const response = await fetchWithTimeout(`${config.apiBaseUrl}/api/v1/admin/backups/${id}/download`, {
    headers: buildApiHeaders({}),
  });
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

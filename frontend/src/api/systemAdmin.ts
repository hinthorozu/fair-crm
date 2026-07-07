import { buildApiHeaders, config } from "../config";
import { apiRequest, ApiError, fetchWithTimeout } from "./client";
import { normalizeStandardListResponse, buildListQueryParams } from "./listTable";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";
import type {
  BackupFormat,
  CreateSystemBackupBatchResponse,
  DatabaseKey,
  DeleteSystemBackupResponse,
  SystemBackup,
  SystemBackupRestoreJobResponse,
} from "../types/systemBackup";

export { ApiError };

function authHeadersOnly(): Record<string, string> {
  const built = buildApiHeaders({});
  const headers: Record<string, string> = {};
  if (typeof built === "object" && !Array.isArray(built) && !(built instanceof Headers)) {
    for (const [key, value] of Object.entries(built)) {
      if (key.toLowerCase() !== "content-type") {
        headers[key] = value;
      }
    }
  }
  return headers;
}

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
  databaseKeys: DatabaseKey[],
  notes?: string | null,
  backupFormat: BackupFormat = "postgresql_dump",
): Promise<CreateSystemBackupBatchResponse> {
  return apiRequest<CreateSystemBackupBatchResponse>("/api/v1/admin/backups", {
    method: "POST",
    body: JSON.stringify({
      database_keys: databaseKeys,
      notes: notes ?? null,
      backup_format: backupFormat,
    }),
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

export async function restoreSystemBackup(backupId: string): Promise<SystemBackupRestoreJobResponse> {
  return apiRequest<SystemBackupRestoreJobResponse>(`/api/v1/admin/backups/${backupId}/restore`, {
    method: "POST",
  });
}

export async function restoreSystemBackupFromUpload(
  file: File,
  databaseKey: DatabaseKey,
  notes?: string | null,
): Promise<SystemBackupRestoreJobResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("database_key", databaseKey);
  if (notes?.trim()) {
    formData.append("notes", notes.trim());
  }

  const response = await fetchWithTimeout(
    `${config.apiBaseUrl}/api/v1/admin/backups/restore/upload`,
    {
      method: "POST",
      headers: authHeadersOnly(),
      body: formData,
    },
  );

  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    if (data && typeof data === "object" && "detail" in data) {
      const value = (data as { detail?: string }).detail;
      if (value) detail = value;
    } else if (typeof data === "string" && data) {
      detail = data;
    }
    throw new ApiError(detail, response.status);
  }

  return data as SystemBackupRestoreJobResponse;
}

export async function deleteSystemBackup(backupId: string): Promise<DeleteSystemBackupResponse> {
  return apiRequest<DeleteSystemBackupResponse>(`/api/v1/admin/backups/${backupId}`, {
    method: "DELETE",
  });
}

export async function listRestoreJobsTable(
  params: ServerTableFetchParams,
): Promise<StandardListResponse<SystemBackupRestoreJobResponse>> {
  const qs = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
  });
  const raw = await apiRequest<unknown>(`/api/v1/admin/backups/restore-jobs?${qs.toString()}`);
  return normalizeStandardListResponse<SystemBackupRestoreJobResponse>(raw);
}

export async function getRestoreJob(id: string): Promise<SystemBackupRestoreJobResponse> {
  return apiRequest<SystemBackupRestoreJobResponse>(`/api/v1/admin/backups/restore-jobs/${id}`);
}

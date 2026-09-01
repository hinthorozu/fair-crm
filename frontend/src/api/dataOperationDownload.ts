import { buildApiHeaders, config } from "../config";
import { getGrantedCorePermissions } from "../permissions/corePermissions";
import { ApiError, fetchWithTimeout } from "./client";

const DATA_OPERATIONS_EXECUTE = "fair_crm.admin.data_operations.execute";
const DATA_OPERATION_DOWNLOAD_DENIED = `Veri işlemi dosyalarını indirme yetkiniz yok (${DATA_OPERATIONS_EXECUTE}).`;

export async function downloadDataOperationFile(
  runId: string,
  fileId: string,
  fileName: string,
): Promise<void> {
  const permissions = getGrantedCorePermissions();
  if (!permissions.has(DATA_OPERATIONS_EXECUTE)) {
    throw new ApiError(DATA_OPERATION_DOWNLOAD_DENIED, 403);
  }

  const response = await fetchWithTimeout(
    `${config.apiBaseUrl}/api/v1/admin/data-operations/runs/${runId}/files/${fileId}/download`,
    { headers: buildApiHeaders({}) },
  );
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

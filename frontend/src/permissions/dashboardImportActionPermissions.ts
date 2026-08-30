import {
  hasGrantedCorePermission,
  type GrantedPermissionCollection,
} from "./corePermissions";

export const DASHBOARD_IMPORT_CREATE = "fair_crm.imports.create";

export function canStartDashboardImport(
  granted: GrantedPermissionCollection,
): boolean {
  return hasGrantedCorePermission(granted, DASHBOARD_IMPORT_CREATE);
}

import {
  hasGrantedCorePermission,
  type GrantedPermissionCollection,
} from "./corePermissions";

export const DASHBOARD_IMPORT_CREATE = "fair_crm.imports.create";
export const DASHBOARD_IMPORT_FAIRS_READ = "fair_crm.fairs.read";

export function canStartDashboardImport(
  granted: GrantedPermissionCollection,
): boolean {
  return (
    hasGrantedCorePermission(granted, DASHBOARD_IMPORT_CREATE) &&
    hasGrantedCorePermission(granted, DASHBOARD_IMPORT_FAIRS_READ)
  );
}

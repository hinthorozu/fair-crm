import {
  hasGrantedCorePermission,
  type GrantedPermissionCollection,
} from "./corePermissions";
import { PERMISSION_EMAIL_ACCOUNTS_READ } from "./navigationPermissions";

export function canOpenDashboardSmtpSettings(
  granted: GrantedPermissionCollection,
): boolean {
  return hasGrantedCorePermission(granted, PERMISSION_EMAIL_ACCOUNTS_READ);
}

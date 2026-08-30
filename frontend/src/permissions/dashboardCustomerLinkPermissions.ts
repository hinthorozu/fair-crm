import {
  hasGrantedCorePermission,
  type GrantedPermissionCollection,
} from "./corePermissions";
import { CUSTOMER_READ } from "./customerPermissions";

export function canOpenDashboardCustomerLink(
  granted: GrantedPermissionCollection,
): boolean {
  return hasGrantedCorePermission(granted, CUSTOMER_READ);
}

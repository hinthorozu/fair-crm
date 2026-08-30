import {
  hasGrantedCorePermission,
  type GrantedPermissionCollection,
} from "./corePermissions";
import { CUSTOMER_CREATE } from "./customerPermissions";
import { PERMISSION_CUSTOMERS_READ } from "./navigationPermissions";

export function canStartDashboardCustomerCreate(
  granted: GrantedPermissionCollection,
): boolean {
  return (
    hasGrantedCorePermission(granted, PERMISSION_CUSTOMERS_READ) &&
    hasGrantedCorePermission(granted, CUSTOMER_CREATE)
  );
}

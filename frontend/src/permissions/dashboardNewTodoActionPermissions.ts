import {
  hasGrantedCorePermission,
  type GrantedPermissionCollection,
} from "./corePermissions";

export const DASHBOARD_TODO_CREATE = "fair_crm.todos.create";

export function canStartDashboardTodoCreate(
  granted: GrantedPermissionCollection,
): boolean {
  return hasGrantedCorePermission(granted, DASHBOARD_TODO_CREATE);
}

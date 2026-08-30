import {
  hasGrantedCorePermission,
  type GrantedPermissionCollection,
} from "./corePermissions";

export const DASHBOARD_TODO_READ = "fair_crm.todos.read";

export function canOpenDashboardTodoList(
  granted: GrantedPermissionCollection,
): boolean {
  return hasGrantedCorePermission(granted, DASHBOARD_TODO_READ);
}

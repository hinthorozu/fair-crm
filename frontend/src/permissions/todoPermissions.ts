import { config } from "../config";

export const TODO_PERMISSION_READ = "fair_crm.todos.read";
export const TODO_PERMISSION_CREATE = "fair_crm.todos.create";
export const TODO_PERMISSION_UPDATE = "fair_crm.todos.update";
export const TODO_PERMISSION_ARCHIVE = "fair_crm.todos.archive";
export const TODO_PERMISSION_DELETE = "fair_crm.todos.delete";

export const TODO_PERMISSIONS_ALL = [
  TODO_PERMISSION_READ,
  TODO_PERMISSION_CREATE,
  TODO_PERMISSION_UPDATE,
  TODO_PERMISSION_ARCHIVE,
  TODO_PERMISSION_DELETE,
] as const;

export type TodoPermissionAction = "read" | "create" | "update" | "archive" | "delete";

const ACTION_TO_PERMISSION: Record<TodoPermissionAction, string> = {
  read: TODO_PERMISSION_READ,
  create: TODO_PERMISSION_CREATE,
  update: TODO_PERMISSION_UPDATE,
  archive: TODO_PERMISSION_ARCHIVE,
  delete: TODO_PERMISSION_DELETE,
};

function parseGrantedPermissions(raw: string | undefined): Set<string> | null {
  if (!raw?.trim()) {
    return null;
  }
  return new Set(
    raw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  );
}

export function getGrantedTodoPermissions(): Set<string> {
  const configured = parseGrantedPermissions(import.meta.env.VITE_GRANTED_PERMISSIONS);
  if (configured) {
    return configured;
  }
  if (config.devBypassEnabled) {
    return new Set(TODO_PERMISSIONS_ALL);
  }
  return new Set(TODO_PERMISSIONS_ALL);
}

export function canPerformTodoAction(
  grantedPermissions: Set<string>,
  action: TodoPermissionAction,
): boolean {
  return grantedPermissions.has(ACTION_TO_PERMISSION[action]);
}

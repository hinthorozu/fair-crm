import { config } from "../config";

export const EMAIL_ACCOUNTS_PERMISSION_READ = "fair_crm.email_accounts.read";
export const EMAIL_ACCOUNTS_PERMISSION_CREATE = "fair_crm.email_accounts.create";
export const EMAIL_ACCOUNTS_PERMISSION_UPDATE = "fair_crm.email_accounts.update";
export const EMAIL_ACCOUNTS_PERMISSION_DELETE = "fair_crm.email_accounts.delete";

export const EMAIL_ACCOUNTS_PERMISSIONS_ALL = [
  EMAIL_ACCOUNTS_PERMISSION_READ,
  EMAIL_ACCOUNTS_PERMISSION_CREATE,
  EMAIL_ACCOUNTS_PERMISSION_UPDATE,
  EMAIL_ACCOUNTS_PERMISSION_DELETE,
] as const;

export type EmailAccountPermissionAction = "read" | "create" | "update" | "delete";

const ACTION_TO_PERMISSION: Record<EmailAccountPermissionAction, string> = {
  read: EMAIL_ACCOUNTS_PERMISSION_READ,
  create: EMAIL_ACCOUNTS_PERMISSION_CREATE,
  update: EMAIL_ACCOUNTS_PERMISSION_UPDATE,
  delete: EMAIL_ACCOUNTS_PERMISSION_DELETE,
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

export function getGrantedPermissions(): Set<string> {
  const configured = parseGrantedPermissions(import.meta.env.VITE_GRANTED_PERMISSIONS);
  if (configured) {
    return configured;
  }
  if (config.devBypassEnabled) {
    return new Set(EMAIL_ACCOUNTS_PERMISSIONS_ALL);
  }
  return new Set(EMAIL_ACCOUNTS_PERMISSIONS_ALL);
}

export function hasPermission(
  grantedPermissions: Set<string>,
  permissionCode: string,
): boolean {
  return grantedPermissions.has(permissionCode);
}

export function canPerformEmailAccountAction(
  grantedPermissions: Set<string>,
  action: EmailAccountPermissionAction,
): boolean {
  return hasPermission(grantedPermissions, ACTION_TO_PERMISSION[action]);
}

export function canSetDefaultEmailAccount(
  account: { is_default: boolean; is_active: boolean },
  grantedPermissions: Set<string>,
): boolean {
  return (
    canPerformEmailAccountAction(grantedPermissions, "update") &&
    account.is_active &&
    !account.is_default
  );
}

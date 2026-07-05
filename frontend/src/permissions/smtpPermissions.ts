import { config } from "../config";

export const SMTP_PERMISSION_READ = "fair_crm.smtp.read";
export const SMTP_PERMISSION_CREATE = "fair_crm.smtp.create";
export const SMTP_PERMISSION_UPDATE = "fair_crm.smtp.update";
export const SMTP_PERMISSION_DELETE = "fair_crm.smtp.delete";

export const SMTP_PERMISSIONS_ALL = [
  SMTP_PERMISSION_READ,
  SMTP_PERMISSION_CREATE,
  SMTP_PERMISSION_UPDATE,
  SMTP_PERMISSION_DELETE,
] as const;

export type SmtpPermissionAction = "read" | "create" | "update" | "delete";

const ACTION_TO_PERMISSION: Record<SmtpPermissionAction, string> = {
  read: SMTP_PERMISSION_READ,
  create: SMTP_PERMISSION_CREATE,
  update: SMTP_PERMISSION_UPDATE,
  delete: SMTP_PERMISSION_DELETE,
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
    return new Set(SMTP_PERMISSIONS_ALL);
  }
  return new Set(SMTP_PERMISSIONS_ALL);
}

export function hasPermission(
  grantedPermissions: Set<string>,
  permissionCode: string,
): boolean {
  return grantedPermissions.has(permissionCode);
}

export function canPerformSmtpAction(
  grantedPermissions: Set<string>,
  action: SmtpPermissionAction,
): boolean {
  return hasPermission(grantedPermissions, ACTION_TO_PERMISSION[action]);
}

export function canSetDefaultSmtpAccount(
  account: { is_default: boolean; is_active: boolean },
  grantedPermissions: Set<string>,
): boolean {
  return (
    canPerformSmtpAction(grantedPermissions, "update") &&
    account.is_active &&
    !account.is_default
  );
}

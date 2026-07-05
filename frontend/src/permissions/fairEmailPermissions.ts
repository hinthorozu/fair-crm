import { config } from "../config";

export const FAIR_EMAIL_PERMISSION_PREVIEW = "fair_crm.fair_emails.preview";
export const FAIR_EMAIL_PERMISSION_SEND = "fair_crm.fair_emails.send";

export const FAIR_EMAIL_PERMISSIONS_ALL = [
  FAIR_EMAIL_PERMISSION_PREVIEW,
  FAIR_EMAIL_PERMISSION_SEND,
] as const;

export type FairEmailPermissionAction = "preview" | "send";

const ACTION_TO_PERMISSION: Record<FairEmailPermissionAction, string> = {
  preview: FAIR_EMAIL_PERMISSION_PREVIEW,
  send: FAIR_EMAIL_PERMISSION_SEND,
};

function parseGrantedPermissions(raw: string | undefined): Set<string> | null {
  if (!raw?.trim()) return null;
  return new Set(
    raw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  );
}

export function getGrantedFairEmailPermissions(): Set<string> {
  if (config.devBypassEnabled) {
    return new Set(FAIR_EMAIL_PERMISSIONS_ALL);
  }
  const configured = parseGrantedPermissions(import.meta.env.VITE_GRANTED_PERMISSIONS);
  if (configured) {
    return configured;
  }
  return new Set(FAIR_EMAIL_PERMISSIONS_ALL);
}

export function canPerformFairEmailAction(
  grantedPermissions: Set<string>,
  action: FairEmailPermissionAction,
): boolean {
  return grantedPermissions.has(ACTION_TO_PERMISSION[action]);
}

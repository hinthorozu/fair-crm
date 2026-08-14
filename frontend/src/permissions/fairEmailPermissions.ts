import { getGrantedCorePermissions } from "./corePermissions";

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

export function getGrantedFairEmailPermissions(): Set<string> {
  return getGrantedCorePermissions();
}

export function canPerformFairEmailAction(
  grantedPermissions: Set<string>,
  action: FairEmailPermissionAction,
): boolean {
  return grantedPermissions.has(ACTION_TO_PERMISSION[action]);
}

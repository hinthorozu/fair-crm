import { getGrantedCorePermissions } from "./corePermissions";

export const FAIR_EMAIL_PERMISSION_READ = "fair_crm.fair_emails.read";
export const FAIR_EMAIL_PERMISSION_EXECUTE = "fair_crm.fair_emails.execute";

// Preview is a read operation; send is an execution operation.
export const FAIR_EMAIL_PERMISSION_PREVIEW = FAIR_EMAIL_PERMISSION_READ;
export const FAIR_EMAIL_PERMISSION_SEND = FAIR_EMAIL_PERMISSION_EXECUTE;

export const FAIR_EMAIL_PERMISSIONS_ALL = [
  FAIR_EMAIL_PERMISSION_READ,
  FAIR_EMAIL_PERMISSION_EXECUTE,
] as const;

export type FairEmailPermissionAction = "preview" | "send";

const ACTION_TO_PERMISSION: Record<FairEmailPermissionAction, string> = {
  preview: FAIR_EMAIL_PERMISSION_READ,
  send: FAIR_EMAIL_PERMISSION_EXECUTE,
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

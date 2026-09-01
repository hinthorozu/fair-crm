import { getGrantedCorePermissions } from "./corePermissions";

export const ADMIN_BACKUP_PERMISSION_CREATE = "fair_crm.admin.backups.create";

export function canCreateAdminBackupOperation(): boolean {
  return getGrantedCorePermissions().has(ADMIN_BACKUP_PERMISSION_CREATE);
}

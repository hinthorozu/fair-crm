import { getGrantedCorePermissions } from "./corePermissions";

export const ADMIN_BACKUP_PERMISSION_CREATE = "fair_crm.admin.backups.create";
export const ADMIN_BACKUP_PERMISSION_DELETE = "fair_crm.admin.backups.delete";
export const ADMIN_BACKUP_PERMISSION_EXECUTE = "fair_crm.admin.backups.execute";

export function canCreateAdminBackupOperation(): boolean {
  return getGrantedCorePermissions().has(ADMIN_BACKUP_PERMISSION_CREATE);
}

export function canDeleteAdminBackupOperation(): boolean {
  return getGrantedCorePermissions().has(ADMIN_BACKUP_PERMISSION_DELETE);
}

export function canExecuteAdminBackupOperation(): boolean {
  return getGrantedCorePermissions().has(ADMIN_BACKUP_PERMISSION_EXECUTE);
}

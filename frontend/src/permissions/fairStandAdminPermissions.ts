import { getGrantedCorePermissions } from "./corePermissions";

export const FAIR_STAND_CATALOG_READ = "fair_crm.admin.fair_stand.catalog.read";
export const FAIR_STAND_CATALOG_CREATE = "fair_crm.admin.fair_stand.catalog.create";
export const FAIR_STAND_CATALOG_UPDATE = "fair_crm.admin.fair_stand.catalog.update";
export const FAIR_STAND_CATALOG_ARCHIVE = "fair_crm.admin.fair_stand.catalog.archive";
export const FAIR_STAND_PREVIEWS_READ = "fair_crm.admin.fair_stand.previews.read";
export const FAIR_STAND_PREVIEWS_CREATE = "fair_crm.admin.fair_stand.previews.create";
export const FAIR_STAND_PREVIEWS_UPDATE = "fair_crm.admin.fair_stand.previews.update";
export const FAIR_STAND_PREVIEWS_ARCHIVE = "fair_crm.admin.fair_stand.previews.archive";
export const FAIR_STAND_SETTINGS_READ = "fair_crm.admin.fair_stand.settings.read";
export const FAIR_STAND_SETTINGS_UPDATE = "fair_crm.admin.fair_stand.settings.update";

export const FAIR_STAND_CATALOG_ADMIN_PERMISSIONS = [
  FAIR_STAND_CATALOG_READ,
  FAIR_STAND_CATALOG_CREATE,
  FAIR_STAND_CATALOG_UPDATE,
  FAIR_STAND_CATALOG_ARCHIVE,
] as const;

export const FAIR_STAND_PREVIEWS_ADMIN_PERMISSIONS = [
  FAIR_STAND_PREVIEWS_READ,
  FAIR_STAND_PREVIEWS_CREATE,
  FAIR_STAND_PREVIEWS_UPDATE,
  FAIR_STAND_PREVIEWS_ARCHIVE,
] as const;

export const FAIR_STAND_SETTINGS_ADMIN_PERMISSIONS = [
  FAIR_STAND_SETTINGS_READ,
  FAIR_STAND_SETTINGS_UPDATE,
] as const;

export function getGrantedFairStandAdminPermissions(): Set<string> {
  return getGrantedCorePermissions();
}
